"""Independent, ordered finishing stages. Originals and intermediate files are retained."""
from pathlib import Path

REFINE_INSTRUCTION = (
    'Improve photographic quality while preserving the existing composition, pose, framing '
    'and recognizable facial identity. Clean up anatomy and fine detail without redesigning the scene.'
)


def finishing_plan(refine=False, identity=False, upscale=0):
    if upscale not in (0, 2, 4):
        raise ValueError('Choose no upscale, 2× or 4×.')
    return (['refine'] if refine else []) + (['identity'] if identity else []) + (['upscale'] if upscale else [])


def run_finishing(selected, master, plan, execute, record):
    current = Path(selected)
    if not current.is_file():
        raise ValueError('Select an existing generated result.')
    if 'identity' in plan and (master is None or not Path(master).is_file()):
        raise ValueError('Identity finishing needs an untouched Character A master reference.')
    results = [current]
    for stage in plan:
        current = Path(execute(stage, current, Path(master) if master else None))
        if not current.is_file():
            raise ValueError('Finishing did not return a saved result.')
        if current in results or (master and current == Path(master)):
            raise ValueError('Finishing must save a separate result without replacing its inputs.')
        results.append(current)
        record(stage, current)
    return results
