"""
Base class of GFlowNet proxies
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Union

import numpy as np
import numpy.typing as npt
import torch
from torchtyping import TensorType

from gflownet.utils.common import set_device, set_float_precision


class Proxy(ABC):
    """
    Generic proxy class
    """

    def __init__(
        self,
        device,
        float_precision,
        reward_function: Union[Callable, str] = "identity",
        reward_function_kwargs: dict = {},
        **kwargs,
    ):
        # Proxy to reward function
        self.reward_function = reward_function
        self._reward_function = self._get_reward_function(
            reward_function, **reward_function_kwargs
        )
        # Device
        self.device = set_device(device)
        # Float precision
        self.float = set_float_precision(float_precision)

    def setup(self, env=None):
        pass

    @abstractmethod
    def __call__(self, states: Union[TensorType, List, npt.NDArray]) -> TensorType:
        """
        Implement  this function to call the get_reward method of the appropriate Proxy
        Class (EI, UCB, Proxy, Oracle etc).

        Parameters
        ----------
            states: ndarray
        """
        pass

    def rewards(self, states: Union[TensorType, List, npt.NDArray]) -> TensorType:
        """
        Computes the rewards of a batch of states.

        The rewards are computed by first calling the proxy function, then
        transforming the proxy values according to the reward function.

        Parameters
        ----------
        states : tensor or list or array
            A batch of states in proxy format.

        Returns
        -------
        tensor
            The reward of all elements in the batch.
        """
        return self.proxy2reward(self(states))

    def log_rewards(self, states: Union[TensorType, List, npt.NDArray]) -> TensorType:
        """
        Computes the log(rewards) of a batch of states.

        The rewards are computed by first calling the proxy function, then
        transforming the proxy values according to the reward function, then taking the
        logarithm.

        Parameters
        ----------
        states : tensor or list or array
            A batch of states in proxy format.

        Returns
        -------
        tensor
            The log reward of all elements in the batch.
        """
        return torch.log(self.proxy2reward(self(states)))

    # TODO: consider adding option to clip values
    # TODO: check that rewards are non-negative
    def proxy2reward(self, proxy_values: TensorType) -> TensorType:
        """
        Transform a tensor of proxy values into rewards.

        Parameters
        ----------
        proxy_values : tensor
            The proxy values corresponding to a batch of states.

        Returns
        -------
        tensor
            The reward of all elements in the batch.
        """
        return self._reward_function(proxy_values)

    def _get_reward_function(self, reward_function: Union[Callable, str], **kwargs):
        r"""
        Returns a callable corresponding to the function that transforms proxy values
        into rewards.

        If reward_function is callable, it is returned as is. If it is a string, it
        must correspond to one of the following options:

            - pow(er): the rewards are the proxy values to the power of beta. See:
              :py:meth:`~gflownet.proxy.base._power()`
            - exp(onential) or boltzmann: the rewards are the negative exponential of
              the proxy values.  See: :py:meth:`~gflownet.proxy.base._exponential()`
            - shift: the rewards are the proxy values shifted by beta.
              See: :py:meth:`~gflownet.proxy.base._shift()`

        Parameters
        ----------
        reward_function : callable or str
            A callable or a string corresponding to one of the pre-defined functions.
        """
        # If reward_function is callable, return it
        if isinstance(reward_function, Callable):
            return reward_function

        # Otherwise it must be a string
        if not isinstance(reward_function, str):
            raise AssertionError(
                "reward_function must be a callable or a string; "
                f"got {type(reward_function)} instead."
            )

        if reward_function.startswith("pow"):
            return Proxy._power(**kwargs)

        if reward_function.startswith("exp") or reward_function == "boltzmann":
            return Proxy._exponential(**kwargs)

    @staticmethod
    def _power(beta: float = 1.0) -> Callable:
        """
        Returns a lambda expression where the inputs (proxy values) are raised to the
        power of beta.

        Parameters
        ----------
        beta : float
            The exponent to which the proxy values are raised.

        Returns
        -------
        A lambda expression where the proxy values raised to the power of beta.
        """
        return lambda proxy_values: proxy_values**beta

    @staticmethod
    def _exponential(beta: float = 1.0) -> Callable:
        """
        Returns a lambda expression where the output is the exponential of the product
        of the input (proxy) values and beta.

        Parameters
        ----------
        beta : float
            The factor by which the proxy values are multiplied.

        Returns
        -------
        A lambda expression that takes the exponential of the proxy values * beta.
        """
        return lambda proxy_values: torch.exp(proxy_values**beta)

    def infer_on_train_set(self):
        """
        Implement this method in specific proxies.
        It should return the ground-truth and proxy values on the proxy's training set.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement `infer_on_train_set`."
        )
