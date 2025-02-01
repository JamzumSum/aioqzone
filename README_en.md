# aioqzone

aioqzone is a python package handling Qzone web login and wrapping some common Qzone Http apis.

[![python](https://img.shields.io/pypi/pyversions/aioqzone?logo=python&logoColor=white)][home]
[![version](https://img.shields.io/pypi/v/aioqzone?logo=python)][pypi]
[![style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![discuss](https://img.shields.io/endpoint?label=Discuss&style=social&url=https%3A%2F%2Ftg.sumanjay.workers.dev%2Faioqzone_chatroom)](https://t.me/aioqzone_chatroom)

English | [简体中文](README.md)

> [!WARNING]
> aioqzone is under active development. Any functionality and interface may be changed.

## Features

### Qzone Feature

- [x] [QR login](src/qqqr/qr/)
- [x] [password login](src/qqqr/up/) (limited)
- [x] [solve slide captcha](src/qqqr/up/captcha/slide)
- [x] [parse select captcha](src/qqqr/up/captcha/select)
- [ ] [pass network environment verification][pychaosvm]
- [x] get complete html feeds
- [x] get feed details
- [x] like/unlike app
- [x] publish/update/delete text feeds
- [x] add comment

### Why using this package?

- [x] full ide typing support (typing)
- [x] api validation (pydantic)
- [x] async design
- [x] complete infrastructure to ease your own develop
- [x] [doc support](https://aioqzone.github.io/aioqzone)

__Working On:__

- [ ] test coverage

## Description

|package    |brief description  |
|-----------|-------------------|
|aioqzone   |qzone api          |
|qqqr       |qzone login        |

## Examples

You can look for these repos for examples in practice.

### aioqzone plugins

- [aioqzone-feed][aioqzone-feed]: aioqzone plugin providing higher level api for processing feed


## License

```
Copyright (C) 2022-2025 aioqzone.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

- [AGPL-3.0](LICENSE)
- [Disclaimers](https://aioqzone.github.io/aioqzone/disclaimers.html)


[home]: https://github.com/aioqzone/aioqzone "Python wrapper for Qzone web login and Qzone http api"
[aioqzone-feed]: https://github.com/aioqzone/aioqzone-feed "aioqzone plugin providing higher level api for processing feed"
[pychaosvm]: https://github.com/aioqzone/pychaosvm "A Python envirionment for Tencent ChaosVM."
[pypi]: https://pypi.org/project/aioqzone
