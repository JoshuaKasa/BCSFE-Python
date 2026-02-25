from bcsfe.core.game.map.zero_legends import Chapter, ChaptersStars, Stage, ZeroLegendsChapters


def test_zero_legends_create_uses_distinct_objects():
    template = ZeroLegendsChapters(
        [
            ChaptersStars(
                0,
                [
                    Chapter(0, 0, 0, [Stage(0), Stage(0)]),
                    Chapter(0, 0, 0, [Stage(0), Stage(0)]),
                ],
            )
        ]
    )

    template.create(1)

    created_map = template.chapters[1]
    assert created_map.chapters[0] is not created_map.chapters[1]
    assert created_map.chapters[0].stages[0] is not created_map.chapters[0].stages[1]
    assert created_map.chapters[0].stages[0] is not created_map.chapters[1].stages[0]

    created_map.chapters[0].stages[0].clear_times = 7
    assert created_map.chapters[0].stages[1].clear_times == 0
    assert created_map.chapters[1].stages[0].clear_times == 0


def test_zero_legends_clear_updates_unlock_state_field():
    chapter = Chapter(0, 0, 0, [Stage(0)])
    chapter.total_stages = 1
    stars = ChaptersStars(0, [chapter, Chapter(0, 0, 0, [Stage(0)])])

    finished = stars.clear_stage(0, 0)

    assert finished is True
    assert stars.chapters[0].unlock_state == 3
    assert stars.chapters[1].unlock_state == 1
