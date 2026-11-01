from abc import ABC, abstractmethod


class BaseCollector(ABC):

    @abstractmethod
    def collect(self):
        """
        Returns a list of Tender objects.
        """
        pass