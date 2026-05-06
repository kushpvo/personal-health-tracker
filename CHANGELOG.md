# Changelog

## [1.2.0](https://github.com/kushpvo/personal-health-tracker/compare/v1.1.1...v1.2.0) (2026-05-06)


### Features

* show computed duration days for supplement doses in UI and PDF export ([#22](https://github.com/kushpvo/personal-health-tracker/issues/22)) ([ca5cf94](https://github.com/kushpvo/personal-health-tracker/commit/ca5cf943c8d55dc4f430660b2aeb7291799592aa))

## [1.1.1](https://github.com/kushpvo/personal-health-tracker/compare/v1.1.0...v1.1.1) (2026-05-06)


### Bug Fixes

* **ci:** tag Docker images with semver versions from manifest on main branch pushes ([#20](https://github.com/kushpvo/personal-health-tracker/issues/20)) ([0dccc62](https://github.com/kushpvo/personal-health-tracker/commit/0dccc62421f9d7a65a4496a87b90d579d1e9474f))

## [1.1.0](https://github.com/kushpvo/personal-health-tracker/compare/v1.0.0...v1.1.0) (2026-05-04)


### Features

* add selective custom PDF export with charts and supplements ([#18](https://github.com/kushpvo/personal-health-tracker/issues/18)) ([006860e](https://github.com/kushpvo/personal-health-tracker/commit/006860edfd317161a67644551972ccf64b65166e))

## 1.0.0 (2026-04-30)


### Features

* add arm64 platform support and remove unraid directory ([#14](https://github.com/kushpvo/personal-health-tracker/issues/14)) ([1af475a](https://github.com/kushpvo/personal-health-tracker/commit/1af475a9c4b72d95202a91d62746fd02347b6525))
* add biological sex field to user profile settings ([8c54534](https://github.com/kushpvo/personal-health-tracker/commit/8c5453451288ef0a4a8f5799650441d4a28e6437))
* add multi-user auth, per-user data isolation, and admin panel ([0d8450a](https://github.com/kushpvo/personal-health-tracker/commit/0d8450ae9a8e56c2182f5f124afe215b647a575b))
* add PDF summary export via reportlab ([#5](https://github.com/kushpvo/personal-health-tracker/issues/5)) ([9d29a4c](https://github.com/kushpvo/personal-health-tracker/commit/9d29a4cdaca2cc8fc531522c8ac8cb61531e4397))
* add re-run OCR endpoint and button for done/failed reports ([#3](https://github.com/kushpvo/personal-health-tracker/issues/3)) ([917f1c5](https://github.com/kushpvo/personal-health-tracker/commit/917f1c58793f42beb28fd500f1c0bec86bb6c9ad))
* add refresh token support with sliding window expiration ([#7](https://github.com/kushpvo/personal-health-tracker/issues/7)) ([ae7e877](https://github.com/kushpvo/personal-health-tracker/commit/ae7e877e580c972ef89c372d2efcc166c4af9f48))
* add search and filter functionality to reports and biomarkers ([#8](https://github.com/kushpvo/personal-health-tracker/issues/8)) ([41bb401](https://github.com/kushpvo/personal-health-tracker/commit/41bb401db6a57328c867dfbdb1748732619c6115))
* add tags and notes to reports ([#9](https://github.com/kushpvo/personal-health-tracker/issues/9)) ([5006e21](https://github.com/kushpvo/personal-health-tracker/commit/5006e219431338a5b728318d986b484239be6ddf))
* add trend alerts — flag biomarkers with ≥20% change or zone crossing ([#6](https://github.com/kushpvo/personal-health-tracker/issues/6)) ([1adcb1f](https://github.com/kushpvo/personal-health-tracker/commit/1adcb1f3475c5eaa6a0df5a79c5f7fb52fe2c304))
* add unknown biomarker bulk resolve UI and API ([#4](https://github.com/kushpvo/personal-health-tracker/issues/4)) ([388bcc9](https://github.com/kushpvo/personal-health-tracker/commit/388bcc96980392efa4a6fe288015bbd4f377da22))
* dashboard grouping toggle — category vs status ([3c19901](https://github.com/kushpvo/personal-health-tracker/commit/3c1990143295f148f65934302dd68afe9d9d5edf))
* delete/add rows in review page + fix unit switching bugs ([32c1c06](https://github.com/kushpvo/personal-health-tracker/commit/32c1c06de0387fd2561b16c21b3b54ee8ecad0aa))
* implement full MVP — backend, frontend, and Docker deployment ([1806c1c](https://github.com/kushpvo/personal-health-tracker/commit/1806c1c5da116f4236a8be343ec5249086bab1e4))
* per-biomarker default unit override with retroactive conversion ([9819cc0](https://github.com/kushpvo/personal-health-tracker/commit/9819cc06f93dd6eca2072021fff1f6b04f71f9ca))
* report detail dashboard — click a report to view its biomarkers ([962d3f0](https://github.com/kushpvo/personal-health-tracker/commit/962d3f0a98492dbc773ffdca6003e894a7799a54))
* seed loader upsert, sort_order/human_matched columns, pipeline sort_order (Tasks 1, 3, 4) ([b369cb9](https://github.com/kushpvo/personal-health-tracker/commit/b369cb97f77290eb78e11084a012c71fe9531c48))
* sex-aware biomarker matching with neutral fallback and metadata sync ([#11](https://github.com/kushpvo/personal-health-tracker/issues/11)) ([bc745c6](https://github.com/kushpvo/personal-health-tracker/commit/bc745c672b2423ae92d66e406912b5e2329ca38c))
* supplement/medication log with dose history and chart overlays ([#10](https://github.com/kushpvo/personal-health-tracker/issues/10)) ([6337911](https://github.com/kushpvo/personal-health-tracker/commit/6337911a3849bdc027ca452b55a4b192eaae4e14))
* upload review flow — backend endpoints, ReviewReport page, frontend wiring ([d584176](https://github.com/kushpvo/personal-health-tracker/commit/d5841767c4165991c17469b42b764eb751534939))


### Bug Fixes

* lint errors and type safety improvements ([90e1cee](https://github.com/kushpvo/personal-health-tracker/commit/90e1ceeb4a90f7e326037c1c1fa2cbd3d94c50e3))
* move hooks before early returns in BiomarkerDetail (Rules of Hooks) ([3c22d25](https://github.com/kushpvo/personal-health-tracker/commit/3c22d2555ca4d72b3cc0c9eea34fcf670a478b61))
* OCR parsing improvements, alias additions, logout and impersonation UX ([73ac1bb](https://github.com/kushpvo/personal-health-tracker/commit/73ac1bbf03fabac38234c5c618a1f475fe366eb6))
* parser correctly handles NAME VALUE UNIT RANGE FLAG lab format ([bab426f](https://github.com/kushpvo/personal-health-tracker/commit/bab426f705c0b225eb3589824f60900a2564bfab))
* restrict CORS to ALLOWED_ORIGINS env var; persist dark mode ([8553795](https://github.com/kushpvo/personal-health-tracker/commit/8553795aecc1dc4edcfc2cf6699b5cc8f3d1b099))
* restrict CORS to ALLOWED_ORIGINS env var; persist dark mode to localStorage ([c6d0466](https://github.com/kushpvo/personal-health-tracker/commit/c6d0466d192b2ec6818c9fdb5f610ebaaec9e1df))
* review and clean up GPT5.4 changes ([b4099a5](https://github.com/kushpvo/personal-health-tracker/commit/b4099a54b70fe54f7aac913d523fc338513439cb))
* review fixes — migration order, Hemoglobin range, CRP/HsCRP alias conflict, Urea BUN alias, expanded matching tests ([c8e7c62](https://github.com/kushpvo/personal-health-tracker/commit/c8e7c62fb2a0e2c031c37f70758961237b8585f7))
* sync biomarker aliases between seed and DB ([ed9e89f](https://github.com/kushpvo/personal-health-tracker/commit/ed9e89fb5751597af011c14daabdb0eaa206fda4))
* trend chart Y-axis values and cleaner zone band visuals ([ae69fe2](https://github.com/kushpvo/personal-health-tracker/commit/ae69fe2588f67498ef8d7ca31c1870aa45643ca9))
* wrap reports.list with arrow function to satisfy TypeScript ([6a10557](https://github.com/kushpvo/personal-health-tracker/commit/6a105579726c2e5e7ea019c88d557ced50779d8e))
