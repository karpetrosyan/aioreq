from enum import Enum
from enum import IntEnum
from enum import StrEnum
from enum import auto


class State(Enum):
    TEST_asd = auto()
    b = auto()


print(State.b)
