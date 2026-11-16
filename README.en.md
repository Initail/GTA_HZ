# GTA_HZ — Hangzhou Journey

A browser city exploration game built with TypeScript and Babylon.js, adapted from [GTA_SZ](https://github.com/linranff/GTA_SZ). The map uses a fixed Hangzhou OSM snapshot and a consistent WGS84 projection at 0.60 scale.

This is **0.16.0-rc.3, an open development candidate**, not a finished city or a long-term stability certification. Existing code includes driving, walking, aircraft, a tank, maps, career/story systems, cafe interactions and lakeside leisure. Bus route integration, landmark acceptance and full gameplay walkthroughs remain open. See [status](docs/STATUS.md) and [roadmap](docs/ROADMAP.md).

Requires Node 24.13.x, npm, Python 3.8+ and a WebGL2 desktop browser:

```sh
npm ci
npm run assets:fetch
npm run dev
```

Open `http://127.0.0.1:5241/` and choose Enter Hangzhou. Assets are a separate, checksum-pinned Release download. `npm test` runs regressions; `npm run build` verifies assets, typechecks and builds the main city and independent combat lab. The dev command builds and serves the output without HMR.

Start with [the documentation index](docs/README.md), [architecture](docs/ARCHITECTURE.md), [contribution guide](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md). Code is MIT. Geographic data and artwork retain their own terms in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Restricted legacy character assets are excluded and replaced with original procedural models. No affiliation with Rockstar Games or depicted organisations is implied.
