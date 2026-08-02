from enum import Enum, auto

class State(Enum);
  IDLE = auto()
  MOVE = auto()
  SCAN = auto()
  # add more states as required

class Machine;
  def __init__(self):
      self.current_state = State.IDLE
      # add as required

  def transition(self, new_state : State):
      match(self.current_state, new_state):
          case (State.IDLE, State.MOVE)
              pass
          # add more cases as necessary
