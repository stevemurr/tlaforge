import unittest

from tlaforge import IntLit, StateMachineSpec


class AuxInitTests(unittest.TestCase):
    def test_emit_uses_explicit_aux_init(self) -> None:
        spec = StateMachineSpec(
            module_name="Counter",
            states=["idle"],
            initial_state="idle",
            aux_vars=["count"],
            aux_init={"count": IntLit(0)},
        )

        emitted = spec.emit()

        self.assertIn("/\\ count = 0", emitted)

    def test_emit_requires_all_aux_init_values(self) -> None:
        spec = StateMachineSpec(
            module_name="Counter",
            states=["idle"],
            initial_state="idle",
            aux_vars=["count"],
        )

        with self.assertRaisesRegex(ValueError, "count"):
            spec.emit()
