# Gather Maps

Gather maps and tilesets for the various events of Codebrick.

## Getting Started

> Tiled is a free and open source, easy to use, and flexible level editor.

* To edit tiled files (.tmx / .tsx), you need to install [tiled](https://www.mapeditor.org/).
* The primary tool for editing tile layers is a `stamp brush` that allows efficient painting and copying of tile areas.

## File Structure

### 📁 maps

map files (.tmx) / background files (.png) / foreground files (.png) divided into project-based directories.

### 📁 tilesets

tileset files (.tml).

## Naming Convention

> It follows the naming convention of [gatertown/mapmaking](https://github.com/gathertown/mapmaking#tileset-naming-convention)

### for tilesets(.tsx)

`group_name_#.x.tsx` Where

* `group` is likely "gather"
* `name` is the tileset name, like "floors" or "decoration"
* `#` is the major version number. Like all versioning systems, the anything contained in a "major version" (to the left of the .) are compatable with themselves.
* `x` is literally "x"

### for tilesheets (".png")

`group_name_#.#.png`

* `group` is likely "gather"
* `name` is the tilesheet name, like "floors" or "decoration"
* `#` is the major version number. Like all versioning systems, the anything contained in a "major version" (to the left of the .) are compatable with themselves.
* `#` is the minor version number. Consider these small changes like little refinements or adding more items without moving anything around.

Examples:

`gather_floors 1.x.tsx` points to `gather_floors_1.3.png`. If the tilesheet is updated (from 1.3 to 1.4) then `gather_floors 1.x.tsx` poitns to `gather_floors_1.4.png`.

## References

* [gathertown/mapmaking](https://github.com/gathertown/mapmaking)
