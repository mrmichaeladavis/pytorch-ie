from typing import Any, Dict

from lightning.pytorch import LightningModule

from pytorch_ie.core.hf_hub_mixin import PyTorchIEModelHubMixin
from pytorch_ie.core.registrable import Registrable


class PyTorchIEModel(PyTorchIEModelHubMixin, LightningModule, Registrable):
    def _config(self) -> Dict[str, Any]:
        config = super()._config() or {}
        config[self.config_type_key] = PyTorchIEModel.name_for_object_class(self)
        # add all hparams
        config.update(self.hparams)
        return config

    def predict(
        self,
        inputs: Any,
        **kwargs,
    ) -> Any:
        return self(inputs, **kwargs)
