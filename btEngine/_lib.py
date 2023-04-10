from collections import OrderedDict
from inspect import currentframe
from itertools import compress
from numbers import Number
from typing import Callable, Optional, Sequence, Union

import numpy as np
import pandas as pd


# def barssince(condition: Sequence[bool], default=np.inf) -> int:
#     return next(compress(range(len(condition)), reversed(condition)), default)


# def cross(series1: Sequence, series2: Sequence) -> bool:
#     return crossover(series1, series2) or crossover(series2, series1)


def crossover(series: pd.DataFrame, firstIndicator, secondIndicator, currentIndex: int) -> bool:
        

        prev1 = series.loc[currentIndex - 1][firstIndicator]
        prev2 = series.loc[currentIndex - 1][secondIndicator]

        curr1 = series.loc[currentIndex][firstIndicator]
        curr2 = series.loc[currentIndex][secondIndicator]
            
        if prev1 < prev2 and curr1 >= curr2:
            return True
        else:
            return False


def crossbelow(series: pd.DataFrame, firstIndicator, secondIndicator, currentIndex: int) -> bool:
        
        prev1 = series.loc[currentIndex - 1][firstIndicator]
        prev2 = series.loc[currentIndex - 1][secondIndicator]


        curr1 = series.loc[currentIndex][firstIndicator]
        curr2 = series.loc[currentIndex][secondIndicator]
            
        if prev1 > prev2 and curr1 <= curr2:
            return True
        else:
            return False
