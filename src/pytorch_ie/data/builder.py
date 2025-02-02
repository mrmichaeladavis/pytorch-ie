import abc
from typing import Any, Dict, Optional, Type, Union, overload

import datasets as hf_datasets
from pytorch_ie.core.document import Document
from pytorch_ie.data.dataset import Dataset, IterableDataset, decorate_convert_to_dict_of_lists


def get_general_dataset_builder_parent_class(
    obj: hf_datasets.builder.DatasetBuilder,
) -> Type[hf_datasets.builder.DatasetBuilder]:
    general_dataset_builder_parent_classes = [
        cls
        for cls in hf_datasets.builder.DatasetBuilder.__subclasses__()
        if cls != PieDatasetBuilder and isinstance(obj, cls)
    ]
    if len(general_dataset_builder_parent_classes) != 1:
        raise TypeError("can not determine general dataset builder parent class of the object")
    return general_dataset_builder_parent_classes[0]


class PieDatasetBuilder(hf_datasets.builder.DatasetBuilder):
    DOCUMENT_TYPE: Optional[Type[Document]] = None

    BASE_DATASET_PATH: Optional[str] = None

    # Define kwargs to create base configs. This should contain config names as keys
    # and the respective config kwargs dicts as values. If the config name is not contained, a new entry
    # {"name": config_name} will be created for it, i.e. the config name is passed as base config name.
    # This default behaviour can be disabled by setting BASE_CONFIG_KWARGS_DICT to None.
    BASE_CONFIG_KWARGS_DICT: Optional[Dict[Optional[str], Dict[str, Any]]] = {}
    # Define base builder kwargs. This should contain config names as keys and the respective
    # builder kwargs dicts as values.
    BASE_BUILDER_KWARGS_DICT: Optional[Dict[Optional[str], Dict[str, Any]]] = None

    def __init__(self, base_dataset_kwargs: Optional[Dict[str, Any]] = None, **kwargs):
        self.base_builder = None
        if self.BASE_DATASET_PATH is not None:
            base_dataset_kwargs = base_dataset_kwargs or {}
            base_builder_kwargs: Dict[str, Any] = {}

            config_name = kwargs.get("config_name", None)

            # get base config kwargs from mapping
            if self.BASE_CONFIG_KWARGS_DICT is not None:
                if config_name in self.BASE_CONFIG_KWARGS_DICT:
                    config_kwargs = self.BASE_CONFIG_KWARGS_DICT[config_name]
                else:
                    # if the config name is not in BASE_CONFIG_KWARGS_DICT,
                    # we pass it as base config name
                    config_kwargs = {"name": config_name}
                base_builder_kwargs.update(config_kwargs)

            # get base builder kwargs from mapping
            if self.BASE_BUILDER_KWARGS_DICT is not None:
                base_builder_kwargs.update(self.BASE_BUILDER_KWARGS_DICT[config_name])

            base_builder_kwargs.update(base_dataset_kwargs)
            self.base_builder = hf_datasets.load.load_dataset_builder(
                path=self.BASE_DATASET_PATH,
                **base_builder_kwargs,
            )
            # Ensure that self and self.base_builder are derived from the same subclass of
            # hf_datasets.builder.DatasetBuilder.
            base_builder_general_parent_class = get_general_dataset_builder_parent_class(
                self.base_builder
            )
            self_general_parent_class = get_general_dataset_builder_parent_class(self)
            if base_builder_general_parent_class != self_general_parent_class:
                raise TypeError(
                    f"The PyTorch-IE dataset builder class '{type(self).__name__}' is derived from "
                    f"{self_general_parent_class}, but the base builder is not which is not allowed. The base builder "
                    f"is of type '{type(self.base_builder).__name__}' that is derived from "
                    f"{base_builder_general_parent_class}. Consider to derive your PyTorch-IE dataset builder "
                    f"'{type(self).__name__}' from a PyTorch-IE variant of "
                    f"'{base_builder_general_parent_class.__name__}'."
                )

            # append the base_builder config_id to the hash, otherwise the base_builder config arguments
            # are not respected in the cache fingerprint
            if "hash" in kwargs:
                kwargs["hash"] = f"{kwargs['hash']}-{self.base_builder.config_id}"

        super().__init__(**kwargs)

    def _info(self):
        return self.base_builder._info()

    def _split_generators(self, dl_manager):
        return self.base_builder._split_generators(dl_manager)

    @abc.abstractmethod
    def _generate_document(self, example, **kwargs):
        pass

    def _generate_document_kwargs(self, dataset):
        return None

    @overload
    def _convert_dataset_single(self, dataset: hf_datasets.Dataset) -> Dataset:
        ...

    @overload
    def _convert_dataset_single(self, dataset: hf_datasets.IterableDataset) -> IterableDataset:
        ...

    def _convert_dataset_single(
        self, dataset: Union[hf_datasets.Dataset, hf_datasets.IterableDataset]
    ) -> Union[Dataset, IterableDataset]:
        if self.DOCUMENT_TYPE is None:
            raise TypeError("the builder has no DOCUMENT_TYPE defined")
        document_type = self.DOCUMENT_TYPE

        fn = decorate_convert_to_dict_of_lists(self._generate_document)
        fn_kwargs = self._generate_document_kwargs(dataset)
        mapped_dataset = dataset.map(fn, fn_kwargs=fn_kwargs)

        if isinstance(mapped_dataset, hf_datasets.Dataset):
            return Dataset.from_hf_dataset(dataset=mapped_dataset, document_type=document_type)
        elif isinstance(mapped_dataset, hf_datasets.IterableDataset):
            return IterableDataset.from_hf_dataset(
                dataset=mapped_dataset, document_type=document_type
            )
        else:
            raise TypeError(
                f"hugginggface dataset has unknown type: {type(mapped_dataset).__name__}. Expected: "
                f"{hf_datasets.Dataset.__name__} or {hf_datasets.IterableDataset.__name__}"
            )

    @overload
    def _convert_datasets(self, datasets: hf_datasets.Dataset) -> Dataset:
        ...

    @overload
    def _convert_datasets(self, datasets: hf_datasets.IterableDataset) -> IterableDataset:
        ...

    @overload
    def _convert_datasets(self, datasets: hf_datasets.DatasetDict) -> hf_datasets.DatasetDict:
        ...

    @overload
    def _convert_datasets(
        self, datasets: hf_datasets.IterableDatasetDict
    ) -> hf_datasets.IterableDatasetDict:
        ...

    def _convert_datasets(
        self,
        datasets: Union[
            hf_datasets.Dataset,
            hf_datasets.IterableDataset,
            hf_datasets.DatasetDict,
            hf_datasets.IterableDatasetDict,
        ],
    ) -> Union[
        Dataset,
        IterableDataset,
        hf_datasets.DatasetDict,
        hf_datasets.IterableDatasetDict,
    ]:
        if isinstance(datasets, dict):
            return type(datasets)(
                {k: self._convert_dataset_single(v) for k, v in datasets.items()}
            )
        else:
            return self._convert_dataset_single(datasets)

    def as_dataset(
        self,
        split: Optional[hf_datasets.Split] = None,
        run_post_process=True,
        verification_mode: Optional[Union[hf_datasets.VerificationMode, str]] = None,
        ignore_verifications="deprecated",
        in_memory=False,
    ) -> Union[Dataset, hf_datasets.DatasetDict]:
        datasets = super().as_dataset(
            split=split,
            run_post_process=run_post_process,
            verification_mode=verification_mode,
            ignore_verifications=ignore_verifications,
            in_memory=in_memory,
        )
        converted_datasets = self._convert_datasets(datasets=datasets)
        return converted_datasets

    def as_streaming_dataset(
        self,
        split: Optional[str] = None,
        base_path: Optional[str] = None,
    ) -> Union[IterableDataset, hf_datasets.IterableDatasetDict]:  # type: ignore
        datasets: Union[
            hf_datasets.IterableDataset, hf_datasets.IterableDatasetDict
        ] = super().as_streaming_dataset(
            split=split, base_path=base_path
        )  # type: ignore
        converted_datasets = self._convert_datasets(datasets=datasets)
        return converted_datasets


class GeneratorBasedBuilder(PieDatasetBuilder, hf_datasets.builder.GeneratorBasedBuilder):
    def _generate_examples(self, *args, **kwargs):
        return self.base_builder._generate_examples(*args, **kwargs)


class ArrowBasedBuilder(PieDatasetBuilder, hf_datasets.builder.ArrowBasedBuilder):
    def _generate_tables(self, *args, **kwargs):
        return self.base_builder._generate_tables(*args, **kwargs)
