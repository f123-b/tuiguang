"""A drama composition must leave the actor visible instead of adding a title slide."""

import pytest
from creator.film import layers_for


@pytest.mark.parametrize("size", [(640, 360), (360, 640), (360, 360), (1920, 1080)])
def test_drama_only_adds_small_ai_label_above_actor(size):
    width, height = size
    shot = {
        "kind": "ai_creative_scene",
        "caption": "Metadata only, not a large title",
        "design": {"layout": "cinema", "motion": "still"},
    }
    _, layers, viewport = layers_for(
        shot, {"width": width, "height": height, "presentation": {"style": "studio"}}
    )
    assert viewport == (0, 0, width, height)
    assert len(layers) == 1
    alpha = layers[0].getchannel("A")
    assert alpha.crop((0, 0, width, int(height * 0.13))).getbbox() is not None
    assert alpha.crop((0, int(height * 0.13), width, height)).getbbox() is None
