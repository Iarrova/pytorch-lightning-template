from argparse import ArgumentParser, Namespace
import seaborn as sns
import matplotlib.pyplot as plt

import torch
import torch.nn as nn

import lightning as L

from torchmetrics import MetricCollection
from torchmetrics.classification import (
    Accuracy,
    Precision,
    Recall,
    AUROC,
    ConfusionMatrix,
)

from utils.config import Config
from utils.json_parser import parse_json

parser: ArgumentParser = ArgumentParser(
    description="Template for PyTorch Lightning prototyping."
)
parser.add_argument(
    "--config_path",
    help="The path to the configuration file to use in training/testing.",
)
args: Namespace = parser.parse_args()

config: Config = parse_json(args.config_path)

L.seed_everything(config.seed)
if torch.cuda.is_available():
    print("[INFO] CUDA is available! Training on GPU...")
else:
    print("[INFO] CUDA is not available. Training on CPU...")


if config.dataset == "CIFAR10":
    from datasets.CIFAR10 import generate_CIFAR10 as generate_dataset

    num_classes = 10
else:
    print("[ERROR] Currently only CIFAR10 dataset is supported. Exiting...")
    exit(1)

train_loader, validation_loader, test_loader, classes = generate_dataset(
    batch_size=config.batch_size,
    validation_size=config.validation_size,
    augment=config.augment,
)


if config.network == "ResNet50":
    from networks.resnet50 import ResNet50 as network
else:
    print("[ERROR] Currently only ResNet50 network is supported. Exiting...")

model: network = network(
    include_top=config.include_top, weights=config.weights, num_classes=num_classes
)


# PyTorch Lightning
class Model(L.LightningModule):
    def __init__(self, model: network, criterion):
        super().__init__()
        self.model: network = model
        self.criterion = criterion

        self.metrics = MetricCollection(
            {
                "accuracy": Accuracy(task="multiclass", num_classes=num_classes),
                "precision": Precision(
                    task="multiclass", num_classes=num_classes, average="macro"
                ),
                "recall": Recall(
                    task="multiclass", num_classes=num_classes, average="macro"
                ),
                "auc": AUROC(task="multiclass", num_classes=num_classes),
            }
        )
        self.confusion_matrix = ConfusionMatrix(
            task="multiclass", num_classes=num_classes
        )

    def step(self, batch):
        inputs, target = batch
        output = self.model(inputs)
        loss = self.criterion(output, target)
        return loss, output, target

    def test_step(self, batch, batch_idx):
        loss, output, target = self.step(batch)
        self.metrics.update(output, target)
        self.confusion_matrix.update(output, target)


criterion = nn.CrossEntropyLoss()
weights_path = f"{config.weights_dir}/{config.weights_path}.ckpt"
model = Model.load_from_checkpoint(weights_path, model=model, criterion=criterion)

trainer = L.Trainer()
trainer.test(model=model, dataloaders=test_loader)

for metric_name, metric_instance in model.metrics.items():
    print(f"{metric_name}: {metric_instance.compute()}")

fig, ax = plt.subplots(figsize=(8, 6))
class_names = list(classes.keys())
sns.heatmap(
    model.confusion_matrix.compute(),
    annot=True,
    fmt="d",
    cmap="Blues",
    xticklabels=class_names,
    yticklabels=class_names,
    ax=ax,
)
ax.tick_params(axis="x", labelrotation=45)
ax.set_xlabel("Predicted Labels")
ax.set_ylabel("True Labels")
ax.set_title("Confusion Matrix")

# Save the confusion matrix as an image
plt.savefig("confusion_matrix.png")
plt.close(fig)
