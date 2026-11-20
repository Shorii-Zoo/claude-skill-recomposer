"""Tests for the deterministic sparse thematic clustering helper."""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import cluster_topics as clustering  # noqa: E402


def item(
    identifier: str,
    kind: str = "plugin",
    name: str = "",
    description: str = "",
    text: str | None = None,
    segments: list[str] | None = None,
) -> dict:
    value = {
        "id": identifier,
        "kind": kind,
        "name": name,
        "description": description,
    }
    if text is not None:
        value["text"] = text
    if segments is not None:
        value["segments"] = segments
    return value


def group_ids(groups: list[dict]) -> list[list[str]]:
    return [[entry["id"] for entry in group["items"]] for group in groups]


def all_entries(groups: list[dict]) -> list[dict]:
    return [entry for group in groups for entry in group["items"]]


class ClusterTopicsTests(unittest.TestCase):
    def test_empty_input_is_safe(self):
        self.assertEqual(clustering.cluster_items([]), [])
        self.assertEqual(clustering.cluster_items(iter(())), [])

    def test_unrelated_items_remain_singletons(self):
        inputs = [
            item("p1", name="quasar-chart", description="Render quasar plots and dashboard panels."),
            item("p2", name="cipher-seal", description="Encrypt archive documents with signatures."),
            item("p3", name="orbit-collector", description="Collect telemetry probes from orbital paths."),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(sorted(group_ids(groups)), [["p1"], ["p2"], ["p3"]])
        self.assertEqual(groups, clustering.cluster_items(list(reversed(inputs))))
        self.assertEqual({entry["id"] for entry in all_entries(groups)}, {"p1", "p2", "p3"})
        self.assertEqual(len(all_entries(groups)), len(inputs))

    def test_related_pair_clusters(self):
        inputs = [
            item(
                "p1",
                name="quasar-chart",
                description="Render quasar plots and dashboard panels from tabular measurements.",
            ),
            item(
                "p2",
                name="quasar-visual",
                description="Compose dashboard charts and quasar plots from tabular measurement tables.",
            ),
            item("p3", name="cipher-seal", description="Encrypt archive documents with signatures."),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(sorted(group_ids(groups)), [["p1", "p2"], ["p3"]])
        component = next(group for group in groups if len(group["items"]) == 2)
        self.assertIs(component["items"][0], inputs[0])
        self.assertIs(component["items"][1], inputs[1])
        self.assertIn("quasar", component["label"])

    def test_topic_anchors_related_plugin_and_unrelated_plugin_stays_singleton(self):
        topic = item(
            "t1",
            kind="topic",
            name="quasar-visualization",
            description="Charts, plots, dashboards and visual encodings of tabular measurements.",
        )
        related = item(
            "p1",
            name="panel-forge",
            description="Forge dashboard plots and charts from tabular measurement rows.",
        )
        unrelated = item(
            "p2",
            name="cipher-seal",
            description="Encrypt archive documents with signatures.",
        )
        groups = clustering.cluster_items([topic, related, unrelated])

        self.assertEqual(sorted(group_ids(groups)), [["p1", "t1"], ["p2"]])
        component = next(group for group in groups if len(group["items"]) == 2)
        self.assertEqual({entry["kind"] for entry in component["items"]}, {"plugin", "topic"})

    def test_late_metadata_in_broad_text_is_sampled(self):
        late_theme = "quasar lattice telemetry " * 20
        inputs = [
            item("p1", name="zephyr-one", text="skill " * 1200 + late_theme),
            item("p2", name="cipher-two", text="skill " * 1200 + late_theme),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(group_ids(groups), [["p1", "p2"]])

    def test_generic_operations_do_not_bridge_segments(self):
        inputs = [
            item(
                "a",
                name="alpha-bundle",
                segments=["audit review", "quasar lattice telemetry"],
            ),
            item(
                "b",
                name="beta-bundle",
                segments=["review audit", "cipher archive encryption"],
            ),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(sorted(group_ids(groups)), [["a"], ["b"]])

    def test_segments_link_local_subtheme_in_broad_bundle(self):
        focused = item(
            "p1",
            name="alpha-probe",
            description="pipeline ingest buffer partition window alert threshold",
            segments=["quasar lattice telemetry"],
        )
        bundle = item(
            "b1",
            name="mixed-bundle",
            segments=[
                "quasar lattice telemetry",
                "cipher archive encryption",
                "nebula orbit position",
                "photo resize crop",
                "audio transcribe speaker",
                "calendar schedule reminder",
                "map route distance",
                "mail delivery inbox",
                "token parse grammar",
                "cache expire policy",
            ],
        )
        groups = clustering.cluster_items([focused, bundle])

        self.assertEqual(group_ids(groups), [["b1", "p1"]])

    def test_strongest_pair_wins_over_weak_early_edge(self):
        inputs = [
            item(
                "a-core",
                name="aaa-core",
                description="quasar lattice telemetry sensor calibration retention",
            ),
            item(
                "b-weak",
                name="bbb-weak",
                description="quasar lattice retention archive",
            ),
            item(
                "c-strong",
                name="ccc-strong",
                description="telemetry sensor calibration retention diagnostic",
            ),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(
            sorted(group_ids(groups)),
            [["a-core", "c-strong"], ["b-weak"]],
        )

    def test_broad_mixed_bundle_does_not_bridge_unrelated_domains(self):
        x1 = item(
            "x1",
            name="alpha-x",
            description="pipeline ingest buffer partition window alert threshold",
            segments=["quasar lattice telemetry"],
        )
        x2 = item(
            "x2",
            name="beta-x",
            description="stream journal shard sample segment replay cursor",
            segments=["telemetry lattice quasar"],
        )
        y1 = item(
            "y1",
            name="gamma-y",
            description="seal signature pin trust revoke rotate policy",
            segments=["cipher archive encryption"],
        )
        y2 = item(
            "y2",
            name="delta-y",
            description="vault credential key derivation salt digest",
            segments=["archive cipher encryption"],
        )
        bridge = item(
            "b",
            name="mixed-bundle",
            segments=[
                "quasar lattice telemetry",
                "cipher archive encryption",
                "nebula orbit position",
                "photo resize crop",
                "audio transcribe speaker",
                "calendar schedule reminder",
                "map route distance",
                "mail delivery inbox",
                "token parse grammar",
                "cache expire policy",
                "chart plot dashboard",
                "invoice ledger reconcile",
            ],
        )
        groups = clustering.cluster_items([bridge, x1, x2, y1, y2])

        x_ids = {"x1", "x2"}
        y_ids = {"y1", "y2"}
        for group in groups:
            member_ids = {entry["id"] for entry in group["items"]}
            self.assertFalse(member_ids & x_ids and member_ids & y_ids)
        self.assertEqual(sorted(group_ids(groups)), [["b", "x1", "x2"], ["y1", "y2"]])
        self.assertEqual(len(all_entries(groups)), 5)

    def test_short_sparse_theme_links_through_overlap(self):
        inputs = [
            item("p1", name="data-viz", description="Charts and plots of tabular measurements."),
            item("p2", name="chart-board", description="Dashboard plots and charts from tabular tables."),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(group_ids(groups), [["p1", "p2"]])

    def test_single_shared_token_does_not_merge(self):
        inputs = [
            item("p1", name="alpha", description="zeta runtime widget"),
            item("p2", name="beta", description="zeta service surface"),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(sorted(group_ids(groups)), [["p1"], ["p2"]])

    def test_reordering_is_stable(self):
        inputs = [
            item("p2", name="zephyr-chart", description="Quasar plots and tabular dashboards."),
            item("p1", name="quasar-visual", description="Dashboard charts and tabular quasar plots."),
            item("p3", name="cipher-seal", description="Encrypt archive documents."),
            item("p4", name="quasar-panel", description="Quasar dashboard panels and plots."),
        ]
        expected = clustering.cluster_items(inputs)

        for ordering in (list(reversed(inputs)), inputs[2:] + inputs[:2], inputs[1:] + inputs[:1]):
            self.assertEqual(clustering.cluster_items(ordering), expected)

    def test_empty_texts_are_singletons(self):
        inputs = [
            item("a", name="Alpha", description="", text=""),
            item("b", name="Beta", description="   ", text=""),
            item("c", name="", description=""),
            item("d", kind="topic", name="", description="", text=""),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(group_ids(groups), [["a"], ["b"], ["c"], ["d"]])
        self.assertEqual(len(all_entries(groups)), len(inputs))
        self.assertEqual({group["label"] for group in groups if not group["items"][0]["name"]}, {"unlabeled"})

    def test_hyphen_snake_names_and_simple_suffixes(self):
        inputs = [
            item(
                "t1",
                kind="topic",
                name="zephyr_visualizations",
                description="Charting tabular measurements as zephyr plots.",
            ),
            item(
                "p1",
                name="zephyr-visualization-kit",
                description="Visualizing zephyr measurements with chart plots.",
            ),
            item("p2", name="cipher-seal", description="Encrypt archive documents."),
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(sorted(group_ids(groups)), [["p1", "t1"], ["p2"]])

    def test_duplicate_ids_are_rejected(self):
        inputs = [
            item("same", name="alpha", description="zeta plots"),
            item("same", kind="topic", name="beta", description="zeta charts"),
        ]
        with self.assertRaisesRegex(ValueError, "duplicate item id"):
            clustering.cluster_items(inputs)

    def test_common_boilerplate_tokens_do_not_merge_large_set(self):
        inputs = [
            item(f"p{index:04d}", name=f"entry{index:04d}", description="zeta omega delta carrier")
            for index in range(200)
        ]
        groups = clustering.cluster_items(inputs)

        self.assertEqual(len(groups), len(inputs))
        self.assertEqual({len(group["items"]) for group in groups}, {1})
        self.assertEqual(len(all_entries(groups)), len(inputs))

    def test_sparse_scale_benchmark(self):
        inputs = []
        themes = 40
        per_theme = 75
        for theme in range(themes):
            for offset in range(per_theme):
                index = theme * per_theme + offset
                descriptor = (
                    f"quasar{theme:03d} zephyr{theme:03d} motif{theme:03d} "
                    f"synthetic record {index}"
                )
                inputs.append(
                    item(
                        f"item-{index:04d}",
                        name=f"series-{index:04d}",
                        description=descriptor,
                        text=f"quasar{theme:03d} zephyr{theme:03d} motif{theme:03d} details",
                    )
                )

        started = time.perf_counter()
        groups = clustering.cluster_items(inputs)
        elapsed = time.perf_counter() - started

        self.assertEqual(len(groups), themes)
        self.assertEqual({len(group["items"]) for group in groups}, {per_theme})
        self.assertEqual(len(all_entries(groups)), len(inputs))
        self.assertLess(elapsed, 15.0, f"clustering 3000 sparse items took {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
