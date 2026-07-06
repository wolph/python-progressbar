import progressbar


def test_unknown_length() -> None:
    pb = progressbar.ProgressBar(
        widgets=[progressbar.AnimatedMarker()],
        max_value=progressbar.UnknownLength,
    )
    assert pb.max_value is progressbar.UnknownLength


def test_unknown_length_default_widgets() -> None:
    # The default widgets picked should work without a known max_value
    pb = progressbar.ProgressBar(max_value=progressbar.UnknownLength).start()
    for i in range(60):
        pb.update(i)
    pb.finish()


def test_unknown_length_at_start() -> None:
    # The default widgets should be picked after we call .start()
    pb = progressbar.ProgressBar().start(max_value=progressbar.UnknownLength)
    for i in range(60):
        pb.update(i)
    pb.finish()

    pb2 = progressbar.ProgressBar().start(max_value=progressbar.UnknownLength)
    for w in pb2.widgets:
        print(type(w), repr(w))
    assert any(isinstance(w, progressbar.Bar) for w in pb2.widgets)


def test_unknown_length_redraws_on_value_change() -> None:
    # With an unknown length and a non-time-sensitive widget (no
    # `INTERVAL`), the bar still needs to redraw whenever the value
    # advances; otherwise it would only ever show the start and finish
    # values. See the `format_label` example.
    pb = progressbar.ProgressBar(
        widgets=[progressbar.FormatLabel('%(value)d')],
        max_value=progressbar.UnknownLength,
    ).start()

    assert pb.poll_interval is None
    pb.previous_value = 2
    pb.value = 3
    # Make sure the min_poll_interval rate limit is not what blocks us
    pb._last_update_timer -= 10
    assert pb._needs_update() is True

    pb.finish()
