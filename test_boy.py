import unittest
from math import pi
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pico2d import (
    SDL_KEYDOWN, SDL_KEYUP, SDLK_ESCAPE, SDLK_LEFT, SDLK_RIGHT, SDLK_SPACE,
)

from boy import Boy


class BoyStateTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch('boy.monotonic', return_value=100.0).start()
        self.addCleanup(patch.stopall)
        self.sprite = Mock()
        patch('boy.load_image', return_value=self.sprite).start()
        patch('boy.get_canvas_width', return_value=800).start()
        self.boy = Boy()

    def send_key(self, key, event_type=SDL_KEYDOWN):
        self.boy.handle_event(SimpleNamespace(type=event_type, key=key))

    def press_space(self):
        self.boy.handle_event(SimpleNamespace(type=SDL_KEYDOWN, key=SDLK_SPACE))

    def fall_asleep(self, now=105.0):
        self.clock.return_value = now
        self.boy.update()
        self.assertEqual(self.boy.state, 'SLEEP')

    def test_initial_idle_and_animation_do_not_move_boy(self):
        for _ in range(1000):
            self.boy.update()
        self.assertEqual(self.boy.state, 'IDLE')
        self.assertEqual((self.boy.x, self.boy.y), (400, 90))
        self.assertEqual(self.boy.frame, 0)
        self.boy.draw()
        self.sprite.clip_draw.assert_called_once_with(0, 300, 100, 100, 400, 90)

    def test_sleep_starts_at_five_seconds(self):
        self.clock.return_value = 104.999
        self.boy.update()
        self.assertEqual(self.boy.state, 'IDLE')
        self.fall_asleep()

    def test_delayed_update_still_enters_sleep(self):
        self.fall_asleep(now=108.0)

    def test_sleep_keeps_fixed_pose_until_woken(self):
        self.fall_asleep()
        self.clock.return_value = 1000.0
        for _ in range(10):
            self.boy.update()
        self.assertEqual(self.boy.state, 'SLEEP')
        self.assertEqual(self.boy.frame, 0)
        self.assertEqual((self.boy.x, self.boy.y), (400, 90))
        for direction in (1, -1):
            with self.subTest(direction=direction):
                self.boy.face_dir = direction
                self.boy.draw()
                row = 300 if direction == 1 else 200
                angle = -pi / 2 if direction == 1 else pi / 2
                self.sprite.clip_composite_draw.assert_called_with(
                    0, row, 100, 100, angle, '', 400, 65, 100, 100,
                )

    def test_space_wakes_and_restarts_full_wait(self):
        self.fall_asleep()
        self.clock.return_value = 120.0
        self.press_space()
        self.assertEqual(self.boy.state, 'IDLE')
        self.assertEqual(self.boy.frame, 0)
        self.boy.draw()
        self.sprite.clip_draw.assert_called_once_with(0, 300, 100, 100, 400, 90)
        self.clock.return_value = 124.999
        self.boy.update()
        self.assertEqual(self.boy.state, 'IDLE')
        self.fall_asleep(now=125.0)

    def test_unrelated_events_and_space_release_do_not_wake(self):
        self.fall_asleep()
        for event in (
            SimpleNamespace(type=SDL_KEYUP, key=SDLK_SPACE),
            SimpleNamespace(type=SDL_KEYUP, key=SDLK_LEFT),
            SimpleNamespace(type=SDL_KEYUP, key=SDLK_RIGHT),
            SimpleNamespace(type=SDL_KEYDOWN, key=SDLK_ESCAPE),
            SimpleNamespace(type=-1),
        ):
            self.boy.handle_event(event)
            self.assertEqual(self.boy.state, 'SLEEP')

    def test_space_during_idle_does_not_reset_wait(self):
        self.clock.return_value = 104.0
        self.press_space()
        self.assertEqual(self.boy.state, 'IDLE')
        self.fall_asleep()

    def test_arrow_keys_move_and_draw_correct_run_direction(self):
        for key, direction, row in ((SDLK_RIGHT, 1, 100), (SDLK_LEFT, -1, 0)):
            with self.subTest(direction=direction):
                self.clock.return_value = 100.0
                self.boy = Boy()
                self.send_key(key)
                self.assertEqual(self.boy.state, 'RUN')
                self.clock.return_value = 100.25
                self.boy.update()
                self.assertEqual(self.boy.x, 400 + direction * 50)
                self.assertEqual(self.boy.y, 90)
                self.assertEqual(self.boy.face_dir, direction)
                self.boy.draw()
                self.sprite.clip_draw.assert_called_with(
                    200, row, 100, 100, self.boy.x, 90,
                )

    def test_releasing_direction_starts_new_idle_wait(self):
        self.send_key(SDLK_RIGHT)
        self.clock.return_value = 110.0
        self.boy.update()
        self.assertEqual(self.boy.state, 'RUN')
        self.press_space()
        self.send_key(SDLK_LEFT, SDL_KEYUP)
        self.assertEqual(self.boy.state, 'RUN')
        self.send_key(SDLK_RIGHT, SDL_KEYUP)
        self.assertEqual(self.boy.state, 'IDLE')
        stopped_x = self.boy.x
        self.clock.return_value = 114.999
        self.boy.update()
        self.assertEqual(self.boy.state, 'IDLE')
        self.assertEqual(self.boy.x, stopped_x)
        self.fall_asleep(now=115.0)

    def test_latest_direction_wins_and_release_restores_held_key(self):
        self.send_key(SDLK_LEFT)
        self.send_key(SDLK_RIGHT)
        self.assertEqual(self.boy.face_dir, 1)
        # Automatic key-repeat for the older key must not change priority.
        self.send_key(SDLK_LEFT)
        self.assertEqual(self.boy.face_dir, 1)
        self.send_key(SDLK_RIGHT, SDL_KEYUP)
        self.assertEqual(self.boy.state, 'RUN')
        self.assertEqual(self.boy.face_dir, -1)
        self.clock.return_value = 100.25
        self.boy.update()
        self.assertEqual(self.boy.x, 350)
        self.send_key(SDLK_LEFT, SDL_KEYUP)
        self.assertEqual(self.boy.state, 'IDLE')
        self.assertEqual(self.boy.held_keys, [])

    def test_key_repeat_does_not_restart_run_animation_or_clock(self):
        self.send_key(SDLK_RIGHT)
        self.clock.return_value = 100.25
        self.boy.update()
        self.clock.return_value = 100.5
        self.send_key(SDLK_RIGHT)
        self.boy.update()
        self.assertEqual(self.boy.x, 500)
        self.assertEqual(self.boy.frame, 5)
        self.send_key(SDLK_RIGHT, SDL_KEYUP)
        self.assertEqual(self.boy.state, 'IDLE')

    def test_movement_speed_is_independent_of_update_frequency(self):
        final_positions = []
        for update_count in (1, 100):
            self.clock.return_value = 100.0
            self.boy = Boy()
            self.send_key(SDLK_RIGHT)
            for step in range(1, update_count + 1):
                self.clock.return_value = 100.0 + step / update_count
                self.boy.update()
            final_positions.append(self.boy.x)
        for position in final_positions:
            self.assertAlmostEqual(position, 600.0)

    def test_run_stays_inside_canvas(self):
        self.send_key(SDLK_RIGHT)
        self.clock.return_value = 110.0
        self.boy.update()
        self.assertEqual(self.boy.x, 750)
        self.send_key(SDLK_RIGHT, SDL_KEYUP)
        self.send_key(SDLK_LEFT)
        self.clock.return_value = 120.0
        self.boy.update()
        self.assertEqual(self.boy.x, 50)

    def test_arrows_wake_directly_into_run_in_pressed_direction(self):
        for key, direction in ((SDLK_LEFT, -1), (SDLK_RIGHT, 1)):
            with self.subTest(direction=direction):
                self.clock.return_value = 100.0
                self.boy = Boy()
                self.fall_asleep()
                self.clock.return_value = 120.0
                self.send_key(key)
                self.assertEqual(self.boy.state, 'RUN')
                self.assertEqual(self.boy.face_dir, direction)
                self.assertEqual(self.boy.held_keys, [key])
                self.assertEqual(self.boy.x, 400)
                self.clock.return_value = 120.25
                self.boy.update()
                self.assertEqual(self.boy.x, 400 + direction * 50)
                self.send_key(key, SDL_KEYUP)
                self.assertEqual(self.boy.state, 'IDLE')
                self.assertEqual(self.boy.idle_started_at, 120.25)


if __name__ == '__main__':
    unittest.main()
