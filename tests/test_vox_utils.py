"""Regression tests for vox_utils: .vox format, geometry and rendering.

Run from the repo root: .venv\\Scripts\\python -m unittest discover tests
"""

import struct
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vox_utils import (MAX_VOXELS, VoxelModel, _chunk, _pack_dict, _read_dict,  # noqa: E402
                       read_vox_file, render_model_to_image, write_vox_file)


def chunk_ids(data: bytes) -> list[bytes]:
    """Top-level chunk ids inside MAIN"""
    ids, pos = [], 20
    while pos < len(data):
        n_content, n_children = struct.unpack_from('<II', data, pos + 4)
        ids.append(data[pos:pos + 4])
        pos += 12 + n_content + n_children
    return ids


def magicavoxel_style_file() -> bytes:
    """A two-model file laid out the way MagicaVoxel 0.99 saves it"""
    def model(voxels):
        return (_chunk(b'SIZE', struct.pack('<III', 4, 4, 4))
                + _chunk(b'XYZI', struct.pack('<I', len(voxels)) + b''.join(bytes(v) for v in voxels)))
    palette = b''.join(bytes((i, 255 - i, 7, 255)) for i in range(256))
    children = (model([(0, 0, 0, 1), (1, 0, 0, 2)]) + model([(3, 3, 3, 5)])
                + _chunk(b'nTRN', b'scene-graph-transform') + _chunk(b'nGRP', b'group')
                + _chunk(b'nSHP', b'shape') + _chunk(b'LAYR', b'layer')
                + _chunk(b'RGBA', palette) + _chunk(b'MATL', b'material'))
    return b'VOX ' + struct.pack('<I', 150) + _chunk(b'MAIN', b'', children)


def scene_file(rotation: str, shape_models=((0,), (1,)), materials=()) -> bytes:
    """A version 200 scene: a root transform and group holding one transform and shape per
    entry of shape_models. The first transform has the given _r and _t "10 20 30"."""
    def model(size, voxels):
        return (_chunk(b'SIZE', struct.pack('<III', *size))
                + _chunk(b'XYZI', struct.pack('<I', len(voxels)) + b''.join(bytes(v) for v in voxels)))
    def transform(node, child, frame):
        return _chunk(b'nTRN', struct.pack('<i', node) + _pack_dict({})
                      + struct.pack('<iiii', child, -1, 0, 1) + _pack_dict(frame))
    nodes = [transform(0, 1, {})]
    children = []
    for k, models in enumerate(shape_models):
        trn, shp = 2 + 2 * k, 3 + 2 * k
        children.append(trn)
        frame = {'_r': rotation, '_t': '10 20 30'} if k == 0 else {'_t': '0 0 0'}
        nodes.append(transform(trn, shp, frame))
        nodes.append(_chunk(b'nSHP', struct.pack('<ii', shp, 0) + struct.pack('<i', len(models))
                            + b''.join(struct.pack('<i', m) + _pack_dict({}) for m in models)))
    group = _chunk(b'nGRP', struct.pack('<ii', 1, 0) + struct.pack('<i', len(children))
                   + b''.join(struct.pack('<i', c) for c in children))
    body = (model((4, 6, 8), [(0, 0, 0, 1), (3, 5, 7, 2)]) + model((2, 2, 2), [(0, 0, 0, 3)])
            + nodes[0] + group + b''.join(nodes[1:])
            + _chunk(b'RGBA', b''.join(bytes((i, i, i, 255)) for i in range(256)))
            + b''.join(_chunk(b'MATL', struct.pack('<i', i) + _pack_dict(attrs)) for i, attrs in materials))
    return b'VOX ' + struct.pack('<I', 200) + _chunk(b'MAIN', b'', body)


def first_transform(path: Path) -> dict:
    """The frame of the transform that places model 0 in scene_file"""
    data = path.read_bytes()
    at = data.index(b'nTRN', data.index(b'nGRP'))
    return _read_dict(data, at + 12 + 4 + 4 + 16)[0]


def materials(model: VoxelModel) -> dict:
    out = {}
    for item in model.layout:
        if isinstance(item, bytes) and item[:4] == b'MATL':
            out[struct.unpack_from('<i', item, 12)[0]] = _read_dict(item, 16)[0]
    return out


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class FormatTests(TempDirTest):
    def test_palette_entry_i_is_color_index_i_plus_1(self):
        model = VoxelModel(2, 2, 2)
        model.set_voxel(0, 0, 0, 1)
        model.set_palette_color(1, 10, 20, 30)
        path = self.dir / "p.vox"
        write_vox_file(path, model)
        data = path.read_bytes()
        rgba = data.index(b'RGBA') + 12
        self.assertEqual(tuple(data[rgba:rgba + 4]), (10, 20, 30, 255))
        self.assertEqual(read_vox_file(path).palette[1], (10, 20, 30, 255))

    def test_main_children_size_matches_file(self):
        model = VoxelModel(3, 3, 3)
        model.fill_box(0, 0, 0, 2, 2, 2, 1)
        path = self.dir / "m.vox"
        write_vox_file(path, model)
        data = path.read_bytes()
        self.assertEqual(struct.unpack_from('<I', data, 16)[0], len(data) - 20)

    def test_magicavoxel_file_keeps_other_models_and_scene(self):
        path = self.dir / "mv.vox"
        original = magicavoxel_style_file()
        path.write_bytes(original)

        model = read_vox_file(path)
        self.assertEqual(model.model_count, 2)
        self.assertEqual(model.voxels, {(0, 0, 0): 1, (1, 0, 0): 2})
        self.assertEqual(model.palette[1], (0, 255, 7, 255))  # RGBA entry 0
        model.set_voxel(2, 2, 2, 3)
        write_vox_file(path, model)

        data = path.read_bytes()
        self.assertEqual(chunk_ids(data), chunk_ids(original))
        for kept in (b'nTRN', b'nGRP', b'nSHP', b'LAYR', b'MATL', bytes((3, 3, 3, 5))):
            self.assertIn(kept, data)
        self.assertEqual(data[data.index(b'RGBA'):], original[original.index(b'RGBA'):])
        self.assertEqual(read_vox_file(path).voxels[(2, 2, 2)], 3)

    def test_failed_write_leaves_file_untouched(self):
        model = VoxelModel(2, 2, 2)
        model.set_voxel(0, 0, 0, 1)
        path = self.dir / "safe.vox"
        write_vox_file(path, model)
        before = path.read_bytes()

        model.voxels[(1, 1, 1)] = 300  # bypasses set_voxel's check
        with self.assertRaises(ValueError):
            write_vox_file(path, model)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(self.dir.iterdir()), [path])  # no temp file left behind

    def test_set_voxel_validates_color_and_counts_clipping(self):
        model = VoxelModel()
        with self.assertRaises(ValueError):
            model.set_voxel(0, 0, 0, 300)
        model.fill_box(250, 0, 0, 260, 0, 0, 1)
        self.assertEqual(len(model.voxels), 6)
        self.assertEqual(model.clipped, 5)

    def test_voxel_cap(self):
        model = VoxelModel()
        with self.assertRaises(ValueError):
            model.fill_box(0, 0, 0, 255, 255, 255, 1)
        self.assertLess(256 * 128 * 64, MAX_VOXELS + 1)


class GeometryTests(unittest.TestCase):
    def test_dilate_at_grid_edge_stays_on_grid(self):
        model = VoxelModel()
        model.fill_box(0, 0, 0, 1, 1, 1, 1)
        model.dilate()
        self.assertTrue(all(min(p) >= 0 for p in model.voxels))
        self.assertGreater(model.clipped, 0)

    def test_scale_up_leaves_no_gaps(self):
        model = VoxelModel(4, 4, 4)
        model.fill_box(0, 0, 0, 3, 3, 3, 1)
        model.scale_model(2, 2, 2)
        self.assertEqual(len(model.voxels), 512)

    def test_erode_removes_surface(self):
        model = VoxelModel()
        model.fill_box(0, 0, 0, 4, 4, 4, 1)
        model.erode()
        self.assertEqual(set(model.voxels), {(x, y, z) for x in range(1, 4) for y in range(1, 4) for z in range(1, 4)})

    def test_flood_fill_fills_closed_box_only(self):
        closed = VoxelModel()
        closed.fill_box(10, 10, 10, 14, 14, 14, 1)
        closed.clear_region(11, 11, 11, 13, 13, 13)
        closed.flood_fill(2)
        self.assertEqual(len(closed.voxels), 125)
        self.assertEqual(closed.get_voxel(12, 12, 12), 2)

        cup = VoxelModel()
        cup.fill_box(0, 0, 0, 39, 39, 39, 1)
        cup.clear_region(1, 1, 1, 38, 38, 39)  # open at the top
        count = len(cup.voxels)
        start = time.perf_counter()
        cup.flood_fill(2)
        self.assertEqual(len(cup.voxels), count)
        self.assertLess(time.perf_counter() - start, 5)

    def test_hollow_pyramid_is_closed(self):
        for base, height in ((9, 5), (12, 3)):
            solid, hollow = VoxelModel(), VoxelModel()
            solid.create_pyramid(0, 0, 0, base, base, height)
            hollow.create_pyramid(0, 0, 0, base, base, height, hollow=True)
            self.assertLess(len(hollow.voxels), len(solid.voxels))
            hollow.flood_fill(1)
            self.assertEqual(len(hollow.voxels), len(solid.voxels), (base, height))

    def test_hollow_sphere_is_inside_solid_sphere(self):
        solid, hollow = VoxelModel(), VoxelModel()
        solid.create_sphere(10, 10, 10, 4, 1)
        hollow.create_sphere(10, 10, 10, 4, 1, hollow=True)
        self.assertTrue(set(hollow.voxels) < set(solid.voxels))
        self.assertNotIn((10, 10, 10), hollow.voxels)

    def test_shapes_rise_along_z_by_default(self):
        model = VoxelModel()
        model.create_cylinder(5, 5, 0, 1, 10)
        lo, hi = model.get_extent()
        self.assertEqual((lo[2], hi[2]), (0, 9))
        self.assertEqual(hi[0] - lo[0], 2)

        cone = VoxelModel()
        cone.create_cone(5, 5, 0, 3, 6)
        self.assertEqual(cone.get_extent()[1][2], 5)

        pyramid = VoxelModel()
        pyramid.create_pyramid(0, 0, 0, 5, 5, 3)
        self.assertEqual([sum(1 for p in pyramid.voxels if p[2] == z) for z in range(3)], [25, 9, 1])

    def test_mirror_between_layers(self):
        model = VoxelModel()
        model.set_voxel(0, 0, 0, 1)
        model.mirror_region(0, 0, 0, 0, 0, 0, 'x', 4.5)
        self.assertIn((9, 0, 0), model.voxels)

    def test_invert_uses_occupied_box(self):
        model = VoxelModel()
        model.set_voxel(5, 5, 5, 1)
        model.set_voxel(6, 5, 5, 1)
        model.invert()
        self.assertEqual(model.voxels, {})


class RenderTests(TempDirTest):
    def test_views_show_nearest_voxel_upright(self):
        from PIL import Image
        model = VoxelModel()
        model.set_voxel(0, 0, 0, 1)   # front-most (smallest y), bottom
        model.set_voxel(0, 3, 0, 2)   # back-most
        model.set_voxel(0, 0, 4, 3)   # top
        model.palette[1] = (255, 0, 0, 255)
        model.palette[2] = (0, 255, 0, 255)
        model.palette[3] = (0, 0, 255, 255)

        def view(angle):
            path = self.dir / f"{angle}.png"
            self.assertTrue(render_model_to_image(model, angle, path))
            img = Image.open(path)
            scale = img.height // 5  # extent is 5 voxels tall
            return lambda col, row: img.getpixel((col * scale, row * scale))[:3]

        front, back = view("front"), view("back")
        self.assertEqual(front(0, 4), (255, 0, 0))  # bottom row, nearest is red
        self.assertEqual(front(0, 0), (0, 0, 255))  # top row is the z=4 voxel
        self.assertEqual(back(0, 4), (0, 255, 0))

    def test_holes_show_darker(self):
        from PIL import Image
        model = VoxelModel()
        model.fill_box(0, 0, 0, 4, 0, 4, 1)   # front wall
        model.fill_box(0, 5, 0, 4, 5, 4, 1)   # back wall, same colour
        model.clear_region(2, 0, 0, 2, 0, 2)  # doorway in the front wall
        path = self.dir / "door.png"
        render_model_to_image(model, "front", path)
        img = Image.open(path)
        scale = img.width // 5
        wall = img.getpixel((0, 4 * scale))
        door = img.getpixel((2 * scale, 4 * scale))
        self.assertLess(sum(door[:3]), sum(wall[:3]) * 0.6)


class SceneTests(TempDirTest):
    def test_growing_keeps_scene_placement(self):
        path = self.dir / "s.vox"
        path.write_bytes(scene_file('4'))  # identity rotation
        model = read_vox_file(path)
        model.set_voxel(9, 0, 0, 1)   # size x 4 -> 10: centre 2 -> 5
        model.set_voxel(0, 0, 12, 1)  # size z 8 -> 13: centre 4 -> 6
        self.assertIsNone(write_vox_file(path, model))
        self.assertEqual(first_transform(path), {'_r': '4', '_t': '13 20 32'})

    def test_rotated_transform_moves_by_rotated_offset(self):
        path = self.dir / "s.vox"
        path.write_bytes(scene_file('17'))  # rows (-y, x, z), as in MagicaVoxel's cars.vox
        model = read_vox_file(path)
        model.set_voxel(9, 0, 0, 1)  # local offset (3, 0, 0)
        write_vox_file(path, model)
        self.assertEqual(first_transform(path)['_t'], '10 23 30')

    def test_shrink_moves_voxels_to_origin_and_keeps_placement(self):
        path = self.dir / "s.vox"
        path.write_bytes(scene_file('4'))
        model = read_vox_file(path)
        model.remove_voxel(0, 0, 0)  # leaves one voxel at (3, 5, 7)
        model.shrink()
        self.assertEqual(model.voxels, {(0, 0, 0): 2})
        write_vox_file(path, model)
        # World position (transform + voxel - size // 2) is unchanged: (10,20,30) + (3,5,7) - (2,3,4)
        self.assertEqual(first_transform(path)['_t'], '11 22 33')
        self.assertEqual(read_vox_file(path).loaded_size, (1, 1, 1))

    def test_animation_frame_gets_a_note(self):
        path = self.dir / "anim.vox"
        path.write_bytes(scene_file('4', shape_models=((0, 1),)))
        model = read_vox_file(path)
        model.set_voxel(9, 0, 0, 1)
        self.assertIn("animation", write_vox_file(path, model))
        self.assertEqual(first_transform(path)['_t'], '10 20 30')

    def test_optimize_palette_refuses_multi_model_files(self):
        path = self.dir / "s.vox"
        path.write_bytes(scene_file('4'))
        with self.assertRaises(ValueError):
            read_vox_file(path).optimize_palette()

    def test_optimize_palette_moves_materials_with_colours(self):
        model = VoxelModel(4, 4, 4)
        model.set_voxel(0, 0, 0, 7)
        model.set_voxel(1, 0, 0, 200)
        model.palette[200] = (9, 8, 7, 255)
        model.layout = ["MODEL", "RGBA"] + [
            _chunk(b'MATL', struct.pack('<i', i) + _pack_dict({'_type': kind}))
            for i, kind in ((1, '_diffuse'), (7, '_metal'), (200, '_emit'))]
        old_palette = list(model.palette)
        self.assertEqual(model.optimize_palette(), 2)
        self.assertEqual(model.voxels, {(0, 0, 0): 1, (1, 0, 0): 2})
        self.assertEqual(model.palette[1], old_palette[7])
        self.assertEqual(model.palette[2], (9, 8, 7, 255))
        self.assertEqual(model.palette[3], old_palette[1])  # unused entries follow, unchanged
        self.assertEqual({i: m['_type'] for i, m in materials(model).items()},
                         {1: '_metal', 2: '_emit', 3: '_diffuse'})


if __name__ == "__main__":
    unittest.main()
