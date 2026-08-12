==================================
Report a transfer's size and speed
==================================

Downloads and copies benefit from three related readouts at once: how
much has moved, how fast on average, and how fast right now -- three
different widgets, not one, since each answers a different question.

.. demo:: howto/file-transfer

``DataSize()`` renders the running total transferred. ``FileTransferSpeed()``
averages the rate over the whole run. ``AdaptiveTransferSpeed()`` instead
reacts to only the last few updates, so it tracks a rate that's currently
speeding up or slowing down -- at the cost of needing several updates
spaced more than a fraction of a second apart before it has enough
history to show anything; expect it to lag behind the other two widgets
for the first few redraws. All three read the same ``bar.update(value)``
call; nothing about updating the bar changes to support them.
