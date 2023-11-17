import time
import copy
import gc

import torch
import numpy as np

from torch import cuda
from torch.nn import BCEWithLogitsLoss
from sklearn.metrics import roc_auc_score
from dataclasses import dataclass


def free_memory():
    """Clears the GPU cache and triggers garbage collection, to reduce OOMs."""
    cuda.empty_cache()
    gc.collect()


def get_masked(target, batch, split_name):
    """
    Applies the mask for a given split but no-ops if the mask isn't present.

    This is useful for shared models where the data may or may not be masked.
    """
    mask_name = f'{split_name}_mask'
    return target if mask_name not in batch else target[batch[mask_name]]


def evaluate_model(model, split_loaders, split_name, device, frac=1.0):
    """
    Main model evaluation loop for validation/testing.

    This is almost identical to the equivalent function in the previous Colab,
    except we calculate the ROC AUC instead of the raw accuracy.
    """
    model.eval()

    y_true_tensors = []
    y_pred_tensors = []

    loader = split_loaders[split_name]
    num_batches = round(frac * len(loader))

    for i, batch in enumerate(loader):
        batch_num = i + 1
        print(f'\r{split_name} batch {batch_num} / {num_batches}', end='')

        batch = batch.to(device)

        with torch.no_grad():
            pred = model(batch)

            # only evaluate the predictions from the split we care about
            eval_pred = pred.detach()
            eval_y = batch["question", "question_correct_answer", "answer"].edge_label.detach()

            y_pred_tensors.append(eval_pred)
            y_true_tensors.append(eval_y)

        if batch_num >= num_batches:
            break

    model.train()

    pred = torch.cat(y_pred_tensors, dim=0).numpy()
    true = torch.cat(y_true_tensors, dim=0).numpy()

    return roc_auc_score(true, pred)


@dataclass(frozen=True)
class EpochResult:
    # "index" of the epoch
    # (this is also discernable from the position in ModelResult.epoch_results)
    epoch_num: int

    # Unix timestamps (seconds) when the epoch started/finished training, but not
    # counting evaluation
    train_start_time: int
    train_end_time: int

    # mean train loss taken across all batches
    mean_train_loss: float

    # accuracy on the training/validation set at the end of this epoch
    train_acc: float
    val_acc: float


@dataclass(frozen=True)
class ModelResult:
    # Unix timestamp for when the model started training
    start_time: int
    # Unix timestamp for when the model completely finished (including evaluation
    # on the test set)
    end_time: int

    # list of EpochResults -- see above
    epoch_results: list

    # model state for reloading
    state_dict: dict

    # final accuracy on the full test set (after all epochs)
    test_acc: float

    def get_total_train_time_sec(self):
        """
        Helper function for calculating the total amount of time spent training, not
        counting evaluation. In other words, this only counts the forward pass, the
        loss calculation, and backprop for each batch.
        """
        return sum([
            er.train_end_time - er.train_start_time
            for er in self.epoch_results])

    def get_total_train_time_min(self):
        """get_total_train_time_sec, converted to minutes. See above."""
        return self.get_total_train_time_sec() // 60


def get_time():
    """Returns the current Unix (epoch) timestamp, in seconds."""
    return round(time.time())


def train_model(model, split_loaders, device, file_name, num_epochs=30, lr=5e-3):
    model = model.to(device)
    model.train()

    opt = torch.optim.Adam(model.parameters(), lr=lr)

    # notice we're using binary classification loss function
    loss_fn = BCEWithLogitsLoss()

    start_time = get_time()
    print(f'start time: {start_time}; will save results to {file_name}')

    train_loader = split_loaders['train']
    epoch_results = []

    for epoch_num in range(1, num_epochs + 1):
        train_start_time = get_time()

        train_losses = []
        y_pred_tensors = []
        y_true_tensors = []

        num_batches = len(train_loader)

        for i, batch in enumerate(train_loader):
            batch_num = i + 1

            # this is a carriage return trick for overwriting past lines
            print(f'\rEpoch {epoch_num}: batch {batch_num} / {num_batches}', end='')

            opt.zero_grad()

            batch = batch.to(device)

            # internally, the model is applied using all the batch's edges (i.e.,
            # batch.edge_index) but only outputs predictions on edges to be labeled
            # (i.e., batch.edge_label_index).
            train_pred = model(batch)

            train_y = batch["question", "question_correct_answer", "answer"].edge_label

            loss = loss_fn(train_pred, train_y)
            loss.backward()

            opt.step()

            y_pred_tensors.append(train_pred.detach())
            y_true_tensors.append(train_y.detach().long())

            train_losses.append(loss.detach().item())

        train_end_time = get_time()
        pred = torch.cat(y_pred_tensors, dim=0).numpy()
        true = torch.cat(y_true_tensors, dim=0).numpy()

        # the training ROC AUC is computed using all the predictions (and ground
        # truth labels) made during the entire epoch, across all batches. Note that
        # this is arguably a bit inconsistent with validation below since it doesn't
        # give the model a "second try" for earlier batches, for which it couldn't
        # have yet applied anything it learned in later batches.
        train_acc = roc_auc_score(true, pred)

        # The validation ROC AUC is computed by running through the validation set
        # at the end of every epoch.
        val_acc = evaluate_model(model, split_loaders, 'val', device)

        epoch_result = EpochResult(
            epoch_num=epoch_num,
            train_start_time=train_start_time,
            train_end_time=train_end_time,
            mean_train_loss=round(np.mean(train_losses), 4),
            train_acc=round(train_acc, 4),
            val_acc=round(val_acc, 4)
        )

        epoch_results.append(epoch_result)
        print(f'\r{epoch_result}')

    state_dict = copy.deepcopy(model.state_dict())
    test_acc = evaluate_model(model, split_loaders, 'test', device)

    model.eval()

    end_time = get_time()
    model_result = ModelResult(start_time, end_time, epoch_results, state_dict, round(test_acc, 4))
    torch.save(model_result, file_name)

    train_time_min = model_result.get_total_train_time_min()
    print(f'\rTest Accuracy: {test_acc:.3f}; Total Train Time: {train_time_min} min')

    return model_result