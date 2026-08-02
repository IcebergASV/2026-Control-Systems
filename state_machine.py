from enum import Enum, auto

class State(Enum):
	IDLE = auto()
	MOVE = auto()
	SCAN = auto()
	# add more here

class Machine:
	def __init__(self):
	   self.current_state = State.IDLE

	def transition(self):
	   match (self.current_state, action):

		case #...
