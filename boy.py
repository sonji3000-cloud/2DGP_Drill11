from math import pi
from time import monotonic

from pico2d import (
    SDL_KEYDOWN, SDL_KEYUP, SDLK_LEFT, SDLK_RIGHT, SDLK_SPACE,
    get_canvas_width, load_image,
)
from transitions import Machine


class Boy:
    IDLE_TIMEOUT = 5.0
    RUN_SPEED = 200.0  # Pixels per second.
    RUN_ANIMATION_FPS = 10.0
    FRAME_SIZE = 100
    AUTO_RUN_SPEED = RUN_SPEED * 2
    AUTO_RUN_SCALE = 1.5
    AUTO_RUN_DURATION = 5.0

    def __init__(self):
        self.x, self.y = 400, 90
        self.frame = 0
        self.face_dir = 1
        self.held_keys = []  # The most recently pressed direction takes priority.
        self.image = load_image('animation_sheet.png')
        self.state_machine = Machine(
            model=self,
            states=[
                {'name': 'IDLE', 'on_enter': '_enter_idle'},
                {'name': 'SLEEP', 'on_enter': '_enter_sleep'},
                {'name': 'RUN', 'on_enter': '_enter_run'},
                {'name': 'AutoRun', 'on_enter': '_enter_auto_run'},
            ],
            initial='IDLE',
            auto_transitions=False,
        )
        # Check the timeout before the fallback animation update.
        self.state_machine.add_transition(
            trigger='idle_tick', source='IDLE', dest='SLEEP',
            conditions='_idle_timed_out',
        )
        # An internal transition updates the animation without leaving IDLE.
        self.state_machine.add_transition(
            trigger='idle_tick', source='IDLE', dest=None,
            after='_update_idle',
        )
        self.state_machine.add_transition(
            trigger='wake_up', source='SLEEP', dest='IDLE',
        )
        self.state_machine.add_transition(
            trigger='start_running', source=['IDLE', 'SLEEP'], dest='RUN',
        )
        self.state_machine.add_transition(
            trigger='stop_running', source='RUN', dest='IDLE',
        )
        self.state_machine.add_transition(
            trigger='run_tick', source='RUN', dest=None, after='_update_run',
        )
        self.state_machine.add_transition(
            trigger='start_auto_run', source='IDLE', dest='AutoRun',
        )
        # Machine initialization does not call the initial state's on_enter.
        self._enter_idle()
        self.last_updated_at = self.idle_started_at

    def update(self):
        now = monotonic()
        delta_time = max(0.0, now - self.last_updated_at)
        self.last_updated_at = now
        if self.is_IDLE():
            self.idle_tick()
        elif self.is_RUN():
            self.run_tick(delta_time)

    def handle_event(self, event):
        if self.is_SLEEP() and event.type == SDL_KEYDOWN and event.key == SDLK_SPACE:
            self.wake_up()
            return

        if event.type not in (SDL_KEYDOWN, SDL_KEYUP):
            return
        if event.key not in (SDLK_LEFT, SDLK_RIGHT):
            return

        if event.type == SDL_KEYDOWN:
            if event.key not in self.held_keys:
                self.held_keys.append(event.key)
        elif event.key in self.held_keys:
            self.held_keys.remove(event.key)

        if self.held_keys:
            self.face_dir = 1 if self.held_keys[-1] == SDLK_RIGHT else -1
            if self.is_IDLE() or self.is_SLEEP():
                self.start_running()
        elif self.is_RUN():
            self.stop_running()

    def _enter_idle(self):
        self.frame = 0
        self.idle_started_at = monotonic()

    def _idle_timed_out(self):
        return monotonic() - self.idle_started_at >= self.IDLE_TIMEOUT

    def _enter_sleep(self):
        self.frame = 0
        self.held_keys.clear()

    def _enter_run(self):
        self.frame = 0
        self.last_updated_at = monotonic()

    def _enter_auto_run(self):
        self.frame = 0
        self.held_keys.clear()
        self.auto_run_started_at = monotonic()
        self.last_updated_at = self.auto_run_started_at

    def _update_run(self, delta_time):
        self.x += self.face_dir * self.RUN_SPEED * delta_time
        self.x = max(50, min(get_canvas_width() - 50, self.x))
        self.frame = (self.frame + self.RUN_ANIMATION_FPS * delta_time) % 8

    def _update_idle(self):
        # Stay at the same position; only the idle animation advances.
        self.frame = (self.frame + 1) % 8

    def draw(self):
        row = 300 if self.face_dir == 1 else 200
        if self.is_SLEEP():
            # Rotate a single idle pose onto the grass without moving the boy.
            angle = -pi / 2 if self.face_dir == 1 else pi / 2
            self.image.clip_composite_draw(
                0, row, 100, 100, angle, '',
                self.x, self.y - 25, 100, 100,
            )
        else:
            if self.is_RUN():
                row = 100 if self.face_dir == 1 else 0
            self.image.clip_draw(int(self.frame) * 100, row, 100, 100, self.x, self.y)

