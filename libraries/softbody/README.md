# softbody

A soft-body (mass-spring) physics engine for Geometry Dash 2.2, written in SPWN. Points are connected by
springs, fall under gravity, bounce off walls and collide with solid collision blocks. Everything runs
as triggers inside the level: Item Edit, Item Compare, Instant Collision and Move triggers.

## Quick start

1. In the GD editor, put one object per point (a circle, say) and give each its own group.
2. Optionally build solid geometry and give it a collision block ID (e.g. block `5b`).
3. Write:

```
sb = import softbody

world = sb.world(gravity = 1800, floor = 0, restitution = 0.4)

// a round jelly: 6 ring points + 1 center point, each in its own group
jelly = world.blob([10g, 11g, 12g, 13g, 14g, 15g], 400, 300, 40, center = 16g)

// a rope hanging from a pinned point
world.rope([
    world.point(30g, 100, 300, pinned = true),
    world.point(31g, 130, 300),
    world.point(32g, 160, 300),
])

world.stats()   // prints how many triggers per frame this costs
world.start()
```

Build with `spwn build level.spwn -i libraries` (or put the library in your SPWN `libraries` folder).

## API

| call | what it does |
|---|---|
| `sb.world(gravity, fps, floor, ceiling, left, right, restitution, friction, air_drag, stiffness, damping, bits, sqrt_iterations, solid, push)` | creates a world. Distances are GD units, `gravity` is units/s² |
| `world.point(group, x?, y?, pinned?, mass?, radius?)` | adds a point; `x`/`y` default to the position of the object in the level |
| `world.spring(a, b, stiffness?, damping?, length?)` | connects two points; rest length defaults to their starting distance |
| `world.rope(points)` | springs between consecutive points |
| `world.mesh(points, max_distance)` | springs between every pair closer than `max_distance` |
| `world.blob(groups, cx, cy, radius, center?)` | ring (plus optional center point) of points with springs |
| `world.impulse(p, vx, vy)` | adds velocity (units/s), meant for your own triggers while it runs |
| `world.set_gravity(g)` | changes gravity at runtime |
| `world.stats()` | prints the approximate trigger count per frame |
| `world.start(driver?)` | builds and starts everything. Call it last. With no `driver` it steps every frame |

Pass `solid = 5b` to `world()` to make points collide with collision blocks of that ID. Each point carries
small sensor blocks and is pushed out of the solid by `push` units per frame.

## Things to know

- **Not tested in real Geometry Dash.** I could not run GD here. The engine is checked against a Python
  reference implementation using a trigger simulator that implements the documented 2.2 trigger
  semantics (`tools/softbody/test_softbody.py`: fall, spring, floor, solid block, triangle, blob, rope).
  All pass, with objects within 0.5 units of the reference.
- It assumes spawned groups run immediately and depth-first, in x order inside a group. SPWN's own
  bit-tests rely on this too.
- Physics steps once per frame, so the speed depends on the frame rate (`fps` should match what players run).
- Cost is high: about 90 triggers per point, 37 per spring and 16 per wall per frame. Keep bodies small
  (a 7-point blob is ~1100 triggers per frame). Use `stats()`.
- Objects move in whole units, so resting points jitter by up to about 1 unit.
- Springs are not drawn; only points have objects.
- `impulse`, `set_gravity` and `driver` with a custom tick are not covered by the simulator tests.
- Items hold floats in 2.2; the engine uses Newton iterations for square roots (Item Edit has none).
