"""End-to-end tests: run server.py over stdio with the MCP client.

Run from the repo root: .venv\\Scripts\\python -m unittest discover tests
"""

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parent.parent


class ServerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.vox_dir = self.root / "vox"
        self.export_dir = self.root / "export"

    def tearDown(self):
        self._tmp.cleanup()

    def run_session(self, steps):
        """Start the server with VOX_DIR/EXPORT_DIR in a temp folder and run steps(session)"""
        async def main():
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(REPO / "server.py")],
                env={**os.environ, "VOX_DIR": str(self.vox_dir), "EXPORT_DIR": str(self.export_dir)},
                cwd=str(self.root),
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await session.initialize()
                    self.assertIn("Z is up", init.instructions or "")
                    return await steps(session)
        return asyncio.run(main())

    def test_tools_and_basic_edit(self):
        async def steps(s):
            tools = (await s.list_tools()).tools
            self.assertEqual(len(tools), 40)
            fill = next(t for t in tools if t.name == "fill_box")
            self.assertEqual(fill.inputSchema["properties"]["x1"]["maximum"], 255)

            await s.call_tool("create_voxel_model", {"filename": "box", "width": 4, "height": 6, "depth": 2})
            result = await s.call_tool("fill_box", {"filename": "box", "x1": 0, "y1": 0, "z1": 0,
                                                    "x2": 3, "y2": 1, "z2": 5, "color_index": 2})
            self.assertFalse(result.isError)
            info = await s.call_tool("get_model_info", {"filename": "box"})
            self.assertIn("4x2x6", info.content[0].text)
        self.run_session(steps)

    def test_errors_are_reported_as_errors(self):
        async def steps(s):
            missing = await s.call_tool("get_model_info", {"filename": "nope"})
            self.assertTrue(missing.isError)
            unknown = await s.call_tool("no_such_tool", {})
            self.assertTrue(unknown.isError)
            await s.call_tool("create_voxel_model", {"filename": "m"})
            out_of_range = await s.call_tool("place_voxel", {"filename": "m", "x": 0, "y": 0, "z": 0,
                                                             "color_index": 300})
            self.assertTrue(out_of_range.isError)
        self.run_session(steps)
        self.assertTrue((self.vox_dir / "m.vox").read_bytes().startswith(b"VOX "))

    def test_names_cannot_leave_vox_folder(self):
        outside = self.root / "outside.vox"
        outside.write_bytes(b"keep")

        async def steps(s):
            await s.call_tool("create_voxel_model", {"filename": "src"})
            for name in ["../outside", str(outside), "a/b", "a\\b", "x.txt:y", "", ".hidden"]:
                copied = await s.call_tool("copy_model", {"source_filename": "src", "target_filename": name})
                self.assertTrue(copied.isError, name)
                deleted = await s.call_tool("delete_model", {"filename": name})
                self.assertTrue(deleted.isError, name)
            snap = await s.call_tool("take_snapshot", {"filename": "src", "snapshot_name": "../../escape"})
            self.assertTrue(snap.isError)
            ok = await s.call_tool("copy_model", {"source_filename": "src.VOX", "target_filename": "my copy"})
            self.assertFalse(ok.isError)
        self.run_session(steps)
        self.assertEqual(outside.read_bytes(), b"keep")
        self.assertTrue((self.vox_dir / "my copy.vox").exists())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["export", "outside.vox", "vox"])

    def test_existing_files_are_not_replaced_silently(self):
        async def steps(s):
            await s.call_tool("create_voxel_model", {"filename": "keep"})
            await s.call_tool("place_voxel", {"filename": "keep", "x": 1, "y": 1, "z": 1})
            again = await s.call_tool("create_voxel_model", {"filename": "keep"})
            self.assertTrue(again.isError)
            self.assertIn("overwrite", again.content[0].text)
            await s.call_tool("create_voxel_model", {"filename": "other"})
            copied = await s.call_tool("copy_model", {"source_filename": "other", "target_filename": "keep"})
            self.assertTrue(copied.isError)
            info = await s.call_tool("get_model_info", {"filename": "keep"})
            self.assertIn("Voxel count: 1", info.content[0].text)

            snap = await s.call_tool("take_snapshot", {"filename": "keep", "snapshot_name": "snap"})
            self.assertFalse(snap.isError)
            again = await s.call_tool("take_snapshot", {"filename": "keep", "snapshot_name": "snap"})
            self.assertTrue(again.isError)
            replaced = await s.call_tool("create_voxel_model", {"filename": "keep", "overwrite": True})
            self.assertFalse(replaced.isError)
        self.run_session(steps)
        self.assertEqual(sorted(p.name for p in self.vox_dir.iterdir()), ["keep.vox", "other.vox"])
        self.assertTrue((self.export_dir / "snap.vox").exists())

    def test_sizes_are_reported_as_magicavoxel_shows_them(self):
        async def steps(s):
            created = await s.call_tool("create_voxel_model", {"filename": "box", "width": 16, "depth": 8, "height": 20})
            self.assertIn("16x8x20 (X x Y x Z)", created.content[0].text)
            info = await s.call_tool("get_model_info", {"filename": "box"})
            self.assertIn("16x8x20", info.content[0].text)
            grown = await s.call_tool("place_voxel", {"filename": "box", "x": 30, "y": 0, "z": 0})
            self.assertIn("changed from 16x8x20 to 31x8x20", grown.content[0].text)
            self.assertIn("Voxels: 0 -> 1", grown.content[0].text)
        self.run_session(steps)

    def test_clipping_is_reported_and_snapshot_renders(self):
        async def steps(s):
            await s.call_tool("create_voxel_model", {"filename": "edge"})
            result = await s.call_tool("fill_box", {"filename": "edge", "x1": 250, "y1": 0, "z1": 0,
                                                    "x2": 255, "y2": 0, "z2": 0})
            self.assertNotIn("Warning", result.content[0].text)
            result = await s.call_tool("extrude_region", {"filename": "edge", "x1": 250, "y1": 0, "z1": 0,
                                                          "x2": 255, "y2": 0, "z2": 0,
                                                          "direction": "x+", "distance": 3})
            self.assertIn("dropped", result.content[0].text)
            snap = await s.call_tool("take_snapshot", {"filename": "edge", "snapshot_name": "edge_snap"})
            self.assertIn("front", snap.content[0].text)
        self.run_session(steps)
        self.assertTrue((self.export_dir / "edge_snap_front.png").exists())


if __name__ == "__main__":
    unittest.main()
