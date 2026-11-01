[SYNTHETIC FIXTURE - not a real release]

# v0.9.0

## Breaking changes
The `generate()` entrypoint no longer accepts a `sampling_params` dict. Callers
must pass a `SamplingParams` object. Passing a dict now raises TypeError.

## Added
Streaming callbacks for partial token output.
