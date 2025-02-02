import lightning.pytorch as pl
import pytest
from torch.utils.data import DataLoader, IterableDataset

from pytorch_ie.models import TransformerTokenClassificationModel
from pytorch_ie.taskmodules import TransformerTokenClassificationTaskModule

MODEL_NAME = "bert-base-cased"


@pytest.fixture
def prepared_taskmodule(documents):
    taskmodule = TransformerTokenClassificationTaskModule(
        tokenizer_name_or_path=MODEL_NAME,
        max_length=128,
    )
    taskmodule.prepare(documents)
    return taskmodule


@pytest.fixture
def model(prepared_taskmodule):
    model = TransformerTokenClassificationModel(
        model_name_or_path=MODEL_NAME,
        num_classes=len(prepared_taskmodule.label_to_id),
        learning_rate=1e-4,
    )
    return model


@pytest.mark.parametrize("as_iterator", [False, True])
def test_transformer_token_classification(model, prepared_taskmodule, documents, as_iterator):
    pl.seed_everything(42)

    num_epochs = 1
    batch_size = 32

    train_dataset = prepared_taskmodule.encode(
        documents,
        encode_target=True,
        document_batch_size=2,
        as_iterator=as_iterator,
        as_dataset=True,
    )

    train_dataloader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=not isinstance(train_dataset, IterableDataset),
        collate_fn=prepared_taskmodule.collate,
    )

    trainer = pl.Trainer(
        fast_dev_run=False,
        max_epochs=num_epochs,
        enable_checkpointing=False,
        precision=32,
    )
    trainer.fit(model, train_dataloader)
