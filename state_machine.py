from enum import Enum, auto

class State(Enum):
    OFF = auto()
    IDLE = auto()
    SEARCH = auto()
    MOVE = auto()
    RETURN = auto()
    MISSION_COMPLETE = auto()


class Machine:
    def __init__(self):
        self.current_state = State.IDLE

    def transition(self, action: str):
        match (self.current_state, action):
            #OFF --> *STATE*
            case (State.OFF, "Setting to Autonomous"):
                self.current_state = State.IDLE
            case (State.OFF, "Moving around"):
                self.current_state = State.MOVE

            #IDLE --> *STATE*
            case (State.IDLE, "Shutting boat off"):
                self.current_state = State.OFF
            case (State.IDLE, "Moving around"):
                self.current_state = State.MOVE
            case (State.IDLE, "Returning home"):
                self.current_state = State.RETURN

			#SEARCH --> *STATE*
            case (State.SEARCH, "Shutting boat off"):
                self.current_state = State.OFF
            case (State.SEARCH, "Idleing"):
                self.current_state = State.IDLE
            case (State.SEARCH, "Moving around"):
                self.current_state = State.MOVE
            case (State.SEARCH, "Returning home"):
                self.current_state = State.RETURN
                
			#MOVE --> *STATE*
            case (State.MOVE, "Shutting boat off"):
                self.current_state = State.OFF
            case (State.MOVE, "Idleing"):
                self.current_state = State.IDLE
            case (State.MOVE, "Searching"):
                self.current_state = State.SEARCH
            case (State.MOVE, "Returning home"):
                self.current_state = State.RETURN

			#RETURN --> *STATE*
            case (State.RETURN, "Shutting boat off"):
                self.current_state = State.OFF
            case (State.RETURN, "Idleing"):
                self.current_state = State.IDLE
            case (State.RETURN, "Finished Mission!"):
                self.current_state = State.MISSION_COMPLETE

			#MISSION_COMPLETE --> *STATE*
            case (State.MISSION_COMPLETE, "Shutting boat off"):
                self.current_state = State.OFF
            case (State.MISSION_COMPLETE, "Idling"):
                self.current_state = State.IDLE
            case (State.MISSION_COMPLETE, "Returning home"):
                self.current_state = State.RETURN