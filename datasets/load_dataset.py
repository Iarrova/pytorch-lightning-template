from utils.config import Config, Datasets


def load_dataset(config: Config):
    if config.dataset == Datasets.CIFAR10:
        from datasets.CIFAR10 import CIFAR10 as Dataset
    elif config.dataset == Datasets.CIFAR100:
        from datasets.CIFAR100 import CIFAR100 as Dataset
    elif config.dataset == Datasets.CIFAR10_128:
        from datasets.CIFAR10_128 import CIFAR10_128 as Dataset
    else:
        print("[ERROR] Invalid dataset passed in configuration file. Exiting...")
        exit(1)

    dataset = Dataset(config.batch_size, config.validation_size, config.augment)

    return dataset
