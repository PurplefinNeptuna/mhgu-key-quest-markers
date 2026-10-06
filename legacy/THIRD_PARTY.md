# Third-party components

Build: maintained Forge headers and pinned libnx/cimgui; repositories/licenses
unchanged. Game binaries/assets and detailed research/hashes stay ignored.
Recipe contains only short exact-build byte windows.

`src/start.S` / `src/plugin.ld` use owned ARM32 plugin scaffolding. Shared
NSO/NRO parsers: `scripts/mhgu_binary.py`.

`src/svc.S` privately adapts libnx `nx/source/kernel/svc32.s`. Original allows
MIT/Apache 2.0; this copy uses MIT. Source SHA-256: candidate manifest.

Copyright (c) 2019 Hydrosphere Developers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
