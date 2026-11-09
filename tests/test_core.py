"""Testes do núcleo (sem Qt nem OpenGL).  Executar:  python -m unittest -v"""

import math
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from editor.core import geometry as geo  # noqa: E402
from editor.core import operations as ops  # noqa: E402
from editor.core.document import Document  # noqa: E402
from editor.core.examples import EXAMPLES  # noqa: E402
from editor.core.fileio import data_to_document, document_to_data, load_document, save_document  # noqa: E402
from editor.core.history import History  # noqa: E402
from editor.core.matrix import Mat3, Transform  # noqa: E402
from editor.core.picking import hit_test  # noqa: E402
from editor.core.shapes import (EllipseShape, GroupShape, PathShape, RectShape,  # noqa: E402
                                RegularPolygonShape, world_matrix)


class MatrixTests(unittest.TestCase):
    def test_elementary(self):
        self.assertEqual(Mat3.translation(3, 4).apply(1, 1), (4, 5))
        x, y = Mat3.rotation(90).apply(1, 0)
        self.assertAlmostEqual(x, 0)
        self.assertAlmostEqual(y, 1)
        self.assertEqual(Mat3.scaling(2, 3).apply(1, 1), (2, 3))
        self.assertEqual(Mat3.shearing(0.5).apply(0, 2), (1, 2))

    def test_composition_order(self):
        # T·R aplicado a (1,0): primeiro roda, depois translada
        m = Mat3.translation(10, 0) @ Mat3.rotation(90)
        x, y = m.apply(1, 0)
        self.assertAlmostEqual(x, 10)
        self.assertAlmostEqual(y, 1)

    def test_rotation_about_point(self):
        m = Mat3.rotation_about(180, 5, 5)
        x, y = m.apply(6, 5)
        self.assertAlmostEqual(x, 4)
        self.assertAlmostEqual(y, 5)

    def test_inverse(self):
        rnd = random.Random(1)
        for _ in range(200):
            t = Transform(rnd.uniform(-500, 500), rnd.uniform(-500, 500), rnd.uniform(-180, 180),
                          rnd.choice([-1, 1]) * rnd.uniform(0.1, 4), rnd.choice([-1, 1]) * rnd.uniform(0.1, 4),
                          rnd.uniform(-2, 2))
            m = t.matrix()
            self.assertTrue((m @ m.inverse()).almost_equal(Mat3.identity(), 1e-9))

    def test_decompose_roundtrip(self):
        rnd = random.Random(2)
        for _ in range(300):
            t = Transform(rnd.uniform(-500, 500), rnd.uniform(-500, 500), rnd.uniform(-179, 179),
                          rnd.choice([-1, 1]) * rnd.uniform(0.1, 4), rnd.choice([-1, 1]) * rnd.uniform(0.1, 4),
                          rnd.uniform(-2, 2))
            m = t.matrix()
            t2 = Transform.from_matrix(m, reference=t)
            self.assertTrue(t2.matrix().almost_equal(m, 1e-7), (t, t2))
            self.assertAlmostEqual(t2.sx, t.sx, places=6)
            self.assertAlmostEqual(t2.rotation, t.rotation, places=6)

    def test_gl_column_major(self):
        m = Mat3([1, 2, 3, 4, 5, 6, 0, 0, 1])
        self.assertEqual(m.to_gl(), [1, 4, 0, 0, 2, 5, 0, 0, 0, 0, 1, 0, 3, 6, 0, 1])


class GeometryTests(unittest.TestCase):
    def test_triangulate_concave(self):
        arrow = [(-60, -20), (20, -20), (20, -45), (70, 0), (20, 45), (20, 20), (-60, 20)]
        tris = geo.triangulate(arrow)
        self.assertEqual(len(tris), len(arrow) - 2)
        area = sum(abs(geo.polygon_area([arrow[a], arrow[b], arrow[c]])) for a, b, c in tris)
        self.assertAlmostEqual(area, abs(geo.polygon_area(arrow)))

    def test_triangulate_clockwise_star(self):
        star = list(reversed(geo.regular_polygon_points(5, 100, 0.4)))
        tris = geo.triangulate(star)
        area = sum(abs(geo.polygon_area([star[a], star[b], star[c]])) for a, b, c in tris)
        self.assertAlmostEqual(area, abs(geo.polygon_area(star)), places=6)

    def test_point_in_polygon(self):
        sq = geo.rect_points(10, 10)
        self.assertTrue(geo.point_in_polygon(0, 0, sq))
        self.assertFalse(geo.point_in_polygon(6, 0, sq))

    def test_rdp(self):
        pts = [(x, math.sin(x / 10.0) * 0.01) for x in range(100)]
        self.assertEqual(len(geo.simplify_rdp(pts, 0.5)), 2)


class DocumentTests(unittest.TestCase):
    def make_doc(self):
        doc = Document()
        layer = doc.active_layer()
        a = RectShape(100, 50)
        a.transform = Transform(100, 100, 30, 1.5, 0.8)
        b = EllipseShape(40, 20)
        b.transform = Transform(300, 200, -20, 1, 2, 0.2)
        c = RegularPolygonShape(5, 40, 0.5)
        c.transform = Transform(200, 400, 10, -1, 1)
        for s in (a, b, c):
            layer.add(s)
        return doc, a, b, c

    def test_group_preserves_world(self):
        doc, a, b, c = self.make_doc()
        before = {s.id: world_matrix(s) for s in (a, b, c)}
        g = ops.group_shapes(doc, [a, b, c])
        self.assertIsInstance(g, GroupShape)
        self.assertEqual(doc.active_layer().objects, [g])
        for s in (a, b, c):
            self.assertTrue(world_matrix(s).almost_equal(before[s.id], 1e-6))
        # rodar e escalar o grupo de forma não uniforme e desagrupar
        g.transform.rotation = 33
        g.transform.sx = 1.7
        g.transform.sy = 0.6
        after = {s.id: world_matrix(s) for s in (a, b, c)}
        ops.ungroup(g)
        for s in (a, b, c):
            self.assertIs(s.parent, doc.active_layer())
            self.assertTrue(world_matrix(s).almost_equal(after[s.id], 1e-6))

    def test_nested_groups_and_zorder(self):
        doc, a, b, c = self.make_doc()
        g1 = ops.group_shapes(doc, [a, b])
        g2 = ops.group_shapes(doc, [g1, c])
        self.assertIs(a.parent, g1)
        self.assertIs(g1.parent, g2)
        layer = doc.active_layer()
        d = RectShape()
        layer.add(d)
        ops.send_to_back([d])
        self.assertIs(layer.objects[0], d)
        ops.bring_forward([d])
        self.assertIs(layer.objects[1], d)

    def test_flip_and_decompose_keep_sign(self):
        doc, a, b, c = self.make_doc()
        ops.flip_shapes([a])
        self.assertLess(a.transform.sx, 0)
        ops.rotate_shapes([a], 25)
        self.assertLess(a.transform.sx, 0)

    def test_history(self):
        doc, a, b, c = self.make_doc()
        h = History(doc)
        a.transform.tx = 999
        self.assertTrue(h.commit("Mover"))
        self.assertFalse(h.commit("Nada"))
        self.assertTrue(h.dirty)
        h.undo()
        self.assertEqual(doc.find(a.id).transform.tx, 100)
        h.redo()
        self.assertEqual(doc.find(a.id).transform.tx, 999)

    def test_save_load(self):
        for name, _desc, build in EXAMPLES:
            doc = build()
            data = document_to_data(doc)
            doc2 = data_to_document(data)
            self.assertEqual(doc.to_dict(), doc2.to_dict(), name)
            self.assertEqual(set(doc.used_image_ids()), set(doc2.images))
        doc = EXAMPLES[3][2]()
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "x.geo")
            save_document(doc, p)
            doc3 = load_document(p)
            self.assertEqual(doc.to_dict(), doc3.to_dict())

    def test_hit_test(self):
        doc, a, b, c = self.make_doc()
        self.assertIs(hit_test(doc, 100, 100, 1), a)
        self.assertIsNone(hit_test(doc, 1000, 1000, 1))
        p = PathShape([(0, 0), (100, 0)], closed=False)
        p.transform.tx, p.transform.ty = 600, 600
        doc.active_layer().add(p)
        self.assertIs(hit_test(doc, 650, 601, 2), p)

    def test_move_to_layer(self):
        doc, a, b, c = self.make_doc()
        g = ops.group_shapes(doc, [a, b])
        w = world_matrix(a)
        other = doc.add_layer("Outra")
        ops.move_to_layer(doc, [a], other)
        self.assertIs(a.parent, other)
        self.assertTrue(world_matrix(a).almost_equal(w, 1e-6))
        self.assertEqual(len(g.children), 1)


if __name__ == "__main__":
    unittest.main()
