from typing import Sequence, Union

import torch

from ignite.exceptions import NotComputableError
from ignite.metrics.metric import Metric, reinit__is_reduced, sync_all_reduce

__all__ = ["MeanSquaredError"]


class MeanSquaredError(Metric):
    r"""Calculates the `mean squared error <https://en.wikipedia.org/wiki/Mean_squared_error>`_.

    .. math:: \text{MSE} = \frac{1}{N} \sum_{i=1}^N \|y_{i} - x_{i}\|^2

    where :math:`y_{i}` is the prediction tensor and :math:`x_{i}` is ground true tensor.

    - ``update`` must receive output of the form ``(y_pred, y)``.

    Args:
        output_transform: a callable that is used to transform the
            :class:`~ignite.engine.engine.Engine`'s ``process_function``'s output into the
            form expected by the metric. This can be useful if, for example, you have a multi-output model and
            you want to compute the metric with respect to one of the outputs.
            By default, metrics require the output as ``(y_pred, y)`` or ``{'y_pred': y_pred, 'y': y}``.
        device: specifies which device updates are accumulated on. Setting the
            metric's device to be the same as your ``update`` arguments ensures the ``update`` method is
            non-blocking. By default, CPU.

    Examples:
        To use with ``Engine`` and ``process_function``, simply attach the metric instance to the engine.
        The output of the engine's ``process_function`` needs to be in the format of
        ``(y_pred, y)`` or ``{'y_pred': y_pred, 'y': y, ...}``. If not, ``output_tranform`` can be added
        to the metric to transform the output into the form expected by the metric.

        ``y_pred`` and ``y`` should have the same shape.

        For more information on how metric works with :class:`~ignite.engine.engine.Engine`, visit :ref:`attach-engine`.

        .. include:: defaults.rst
            :start-after: :orphan:

        .. testcode::

            metric = MeanSquaredError()
            metric.attach(default_evaluator, 'mse')
            preds = torch.tensor([
                [1, 2, 4, 1],
                [2, 3, 1, 5],
                [1, 3, 5, 1],
                [1, 5, 1 ,11]
            ])
            target = preds * 0.75
            state = default_evaluator.run([[preds, target]])
            print(state.metrics['mse'])

        .. testoutput::

            3.828125
    """

    _state_dict_all_req_keys = ("_sum_of_squared_errors", "_num_examples")

    @reinit__is_reduced
    def reset(self) -> None:
        self._sum_of_squared_errors = torch.tensor(0.0, device=self._device)
        self._num_examples = 0

    @reinit__is_reduced
    def update(self, output: Sequence[torch.Tensor]) -> None:
        y_pred, y = output[0].detach(), output[1].detach()
        squared_errors = torch.pow(y_pred - y.view_as(y_pred), 2)
        self._sum_of_squared_errors += torch.sum(squared_errors).to(self._device)
        self._num_examples += y.shape[0]

    @sync_all_reduce("_sum_of_squared_errors", "_num_examples")
    def compute(self) -> Union[float, torch.Tensor]:
        if self._num_examples == 0:
            raise NotComputableError("MeanSquaredError must have at least one example before it can be computed.")
        return self._sum_of_squared_errors.item() / self._num_examples
