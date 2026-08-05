# PortMasters Variants

Welcome to the sandbox. Grab a coffee and pull up a chair.

PortMasters is a browser based maritime trading game focused on resource management and risk mitigation. Captains sail the ancient Silk Road, hire artisans, manage cargo holds, and attempt to survive eight tense voyages without facing bankruptcy. The core loop revolves around production chains, market speculation, and squeezing maximum value from every trade route.

## The 1.0 Baseline and The Multiplayer Build

The original 1.0 release, housed [here](https://github.com/LostInHustle/PortMasters), delivers a tight and focused solitary experience. The original version remains pure and untouched, serving as the foundational baseline. The Variants repository introduces a robust social layer to transform a solitary voyage into a bustling digital port.

The following list details how the current multiplayer build diverges from the 1.0 baseline:

- Shared Seas: Multiple captains sail simultaneously. A live sidebar displays online status, current voyage phases, and hoarded gold for every active player.
- Direct Messaging: A sleek chat system allows players to negotiate, celebrate massive payouts, or discuss broker rolls while fleets sit in drydock.
- Persistent Progress: Runs tie to secure accounts. Save states move to a cloud database, meaning sessions can close and reopen on different devices without losing hard earned cargo.
- Account Security: Proper session management and password hashing ensure professional security standards for all browser based interactions.

## Future Builds

Treating the repository as an experimental playground allows for rapid iteration and the shipping of wild new game flavors without compromising the stability of the original release. Future builds will explore several new directions:

- Cooperative Fleets: Sharing a single cargo hold and splitting maintenance costs with a partner. Synchronous mechanics will require coordinating artisan assignments in real time.
- Asynchronous Tournaments: Weekly reset leaderboards where all players play the same seeded random number generator layout, competing for the highest reputation score before the weekend ends.
- Roguelike Drafts: A mutation mode where ship modules permanently alter runs in unpredictable ways, adding heavy replayability to the core loop.
- Engine Upgrades: Continuous optimization of the WebSocket architecture to handle larger lobbies and smoother real time updates as social features expand.

## Under the Hood

For developers interested in the technical stack, the multiplayer backend runs on Python Flask and SocketIO, with SQLAlchemy handling the persistent database. The frontend remains pure vanilla JavaScript. Keeping the client lightweight, fast, and completely free of heavy framework overhead ensures maximum performance and minimal load times.

## Setting Sail

Getting a local server running requires minimal effort. Install the Python requirements, spin up the application, and open multiple browser windows to register a crew.

Fair winds and full cargo holds.
