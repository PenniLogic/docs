"""The adr/LAYOUT.md validation exercises for the ADR layout generator (PenniLogic/docs#146).

Every exercise runs on the split-built baseline fixture, never the live tree, and the git exercises
run again from a fixture with two published records and one supersession. Git repositories are
local and isolated (own HOME and config, no hooks); clones use ``file://`` transport only. No
custom or union merge driver and no discarded first squash is used anywhere.

1. Partial initial split (LAYOUT.md "Partial initial split"): an injected write failure in the
   middle of ``split`` leaves a partial layout that ``split`` refuses to overwrite and the monolith
   README untouched; the isolated reconstruction in a separate empty scratch directory reproduces
   every retained file byte for byte, supplies the individually identified missing initial files
   (never its README), and README-only regeneration completes the layout.
2. Depth-1 ``file://`` clones (LAYOUT.md "Validation"): a committed positive candidate validates in a
   one-commit clone with no parent history; negative candidates — a hand-edited generated slot and
   an undated edit of an accepted record — fail closed in the same kind of clone.
3. Nine-branch adjacent-pair squash-merge matrix (LAYOUT.md "Validation"): nine independent ordinary
   branches from one baseline are serially squash-merged and committed in forward, reverse and
   alternating order and in both orders of every adjacent pair, checking strict validation, exact
   rendering, owner retention and the cumulative source set after every merge.
"""

import contextlib
import io
import itertools
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_adr_layout import (  # noqa: E402
    GIT, LEGACY_FILES, MONEY, CRYPTO, REFERENCE, SPLIT_OUTPUT, Baseline, GitScratchCase, adr, make_writable,
    slot_rows, source,
)

BASELINE_SUMMARY = {"legacy": 14, "allocations": 9, "published": 0, "pending": 9, "superseded": 0}
INPUTS = [name for name in SPLIT_OUTPUT if name != "README.md"]  # everything split writes except the index


def setUpModule():
    Baseline.build()


def allocations():
    return [(item["number"], item["ticket"]) for item in json.loads(Baseline.read("reservations.json"))["items"]]


def alternating(numbers):
    """Outside-in interleaving: first, last, second, second to last, ..."""
    half = (len(numbers) + 1) // 2
    pairs = itertools.zip_longest(numbers[:half], reversed(numbers[half:]))
    return [number for pair in pairs for number in pair if number is not None]


class SplitRecoveryTests(unittest.TestCase):
    """LAYOUT.md "Partial initial split": injected mid-split failure and the isolated reconstruction."""

    WRITES = len(SPLIT_OUTPUT)  # fourteen legacy sources, manifest, reservations, registry, README

    def setUp(self):
        self.root = self.scratch_root()
        self.adr = self.root / "adr"

    def scratch_root(self):
        """An empty scratch directory holding only the verified reference as reference and README."""
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        self.addCleanup(self.cleanup, directory, root)
        (root / "adr").mkdir()
        (root / "adr" / "presplit-reference.md").write_bytes(REFERENCE)
        (root / "adr" / "README.md").write_bytes(REFERENCE)
        return root

    def cleanup(self, directory, root):
        make_writable(root)
        directory.cleanup()

    def files(self, root=None):
        return {path.name: path.read_bytes() for path in sorted((root or self.root).joinpath("adr").iterdir())}

    def inputs(self):
        return {name: data for name, data in self.files().items() if name not in ("README.md", "presplit-reference.md")}

    def inject_failure_at(self, write_number):
        """Fail the ``write_number``-th output replacement of ``split``; the failure propagates."""
        calls = itertools.count(1)
        real = adr._replace

        def failing(src, dst):
            if next(calls) == write_number:
                raise OSError(f"injected failure at write {write_number}")
            return real(src, dst)

        with mock.patch.object(adr, "_replace", failing):
            with self.assertRaisesRegex(OSError, f"injected failure at write {write_number}"):
                adr.split(self.root)
        self.assertEqual([path.name for path in self.adr.glob(".*.tmp")], [], "the failed write leaves no temporary")
        self.assertEqual(self.files()["README.md"], REFERENCE, "the monolith README is untouched")

    def reconstruct(self):
        """The isolated reconstruction: the same reviewed script, a separate empty scratch, CLI only."""
        scratch = self.scratch_root()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(adr.main(["split", "--root", str(scratch)]), 0)
            self.assertEqual(adr.main(["check", "--root", str(scratch)]), 0)
        self.assertIn("Split complete: 14 legacy records, 9 allocations, 0 published", out.getvalue())
        for name in SPLIT_OUTPUT:
            self.assertEqual((scratch / "adr" / name).read_bytes(), Baseline.read(name))
        return scratch

    def test_injected_mid_split_failure_leaves_a_partial_layout_that_split_refuses(self):
        self.inject_failure_at(6)
        retained = self.inputs()
        self.assertEqual(sorted(retained), LEGACY_FILES[:5])
        before = self.files()
        with self.assertRaisesRegex(adr.LayoutError, "refusing to overwrite an already split layout: "
                                    "ADR-001.md, ADR-002.md, ADR-003.md, ADR-004.md, ADR-005.md"):
            adr.split(self.root)
        self.assertEqual(self.files(), before, "a refused split changes nothing")
        with self.assertRaisesRegex(adr.LayoutError, "legacy-bodies.json is missing"):
            adr.validate_sources(self.root)
        with self.assertRaisesRegex(adr.LayoutError, "legacy-bodies.json is missing"):
            adr.check_layout(self.root)
        # A ticket-scoped render is no recovery path either: it needs the existing projection.
        with self.assertRaisesRegex(adr.LayoutError, "legacy-bodies.json is missing"):
            adr.render(self.root, MONEY)

    def test_isolated_reconstruction_supplies_the_missing_initial_files_and_readme_regeneration_completes(self):
        self.inject_failure_at(6)
        retained = self.inputs()
        scratch = self.reconstruct()
        for name, data in retained.items():
            with self.subTest(retained=name):
                self.assertEqual(data, (scratch / "adr" / name).read_bytes(), "headers and bodies match the reconstruction")
        missing = [name for name in INPUTS if name not in retained]
        self.assertEqual(missing, LEGACY_FILES[5:] + ["legacy-bodies.json", "reservations.json", "accepted-records.json"])
        for name in missing:
            shutil.copy2(scratch / "adr" / name, self.adr / name)
            self.assertEqual(
                stat.S_IMODE(os.stat(self.adr / name).st_mode), stat.S_IMODE(os.stat(scratch / "adr" / name).st_mode)
            )
        self.assertEqual(self.files()["README.md"], REFERENCE, "the reconstruction's README is never copied")
        adr.validate_sources(self.root)  # the now-complete inputs validate without the damaged index
        inputs = self.inputs()
        self.assertEqual(adr.render(self.root), ["adr/README.md"], "README-only regeneration")
        self.assertEqual(adr.check_layout(self.root), BASELINE_SUMMARY)
        self.assertEqual(adr.render(self.root), [], "a second render produces identical bytes")
        self.assertEqual(self.inputs(), inputs, "no retained or copied input changed")
        self.assertEqual(self.files()["README.md"], Baseline.read("README.md"))
        for name in SPLIT_OUTPUT:
            self.assertEqual(self.files()[name], Baseline.read(name))

    def test_failure_on_the_final_readme_write_needs_only_readme_regeneration(self):
        self.inject_failure_at(self.WRITES)
        self.assertEqual(sorted(self.inputs()), sorted(INPUTS))
        adr.validate_sources(self.root)
        with self.assertRaisesRegex(adr.LayoutError, "refusing to overwrite an already split layout"):
            adr.split(self.root)
        with self.assertRaisesRegex(adr.LayoutError, "does not match the rendered layout: generated slot ADR-001 differs"):
            adr.check_layout(self.root)  # the README is still the monolith
        self.assertEqual(adr.render(self.root), ["adr/README.md"])
        self.assertEqual(adr.check_layout(self.root), BASELINE_SUMMARY)
        for name in SPLIT_OUTPUT:
            self.assertEqual(self.files()[name], Baseline.read(name))

    def test_failure_before_the_registry_write_is_completed_by_an_unscoped_render(self):
        self.inject_failure_at(self.WRITES - 1)
        self.assertNotIn("accepted-records.json", self.inputs())
        adr.validate_sources(self.root)
        with self.assertRaisesRegex(adr.LayoutError, "does not match the rendered layout: generated slot ADR-001 differs"):
            adr.check_layout(self.root)  # the README is still the monolith
        with self.assertRaisesRegex(adr.LayoutError, "accepted-records.json is missing; a ticket-scoped render never creates"):
            adr.render(self.root, MONEY)
        self.assertEqual(adr.render(self.root), ["adr/README.md", "adr/accepted-records.json"])
        self.assertEqual(adr.check_layout(self.root), BASELINE_SUMMARY)
        for name in SPLIT_OUTPUT:
            self.assertEqual(self.files()[name], Baseline.read(name))

    def test_reconstruction_never_replaces_a_differing_retained_file_or_a_downstream_record(self):
        """A published downstream record or a differing retained source stops the copy step."""
        self.inject_failure_at(6)
        self.adr.joinpath("ADR-015.md").write_bytes(source().encode("utf-8"))
        edited = self.adr / "ADR-003.md"
        edited.write_bytes(edited.read_bytes().replace(b"**Revisit if:**", b"**Revisit when:**"))
        with self.assertRaisesRegex(adr.LayoutError, "already split layout: ADR-001.md, .*ADR-015.md"):
            adr.split(self.root)
        retained = self.inputs()
        scratch = self.reconstruct()
        reconstruction = self.files(scratch)
        self.assertNotIn("ADR-015.md", reconstruction, "initial-split output never contains a downstream record")
        downstream = [name for name in retained if name not in reconstruction]
        differing = [name for name in retained if name in reconstruction and retained[name] != reconstruction[name]]
        self.assertEqual((downstream, differing), (["ADR-015.md"], ["ADR-003.md"]))
        # The procedure stops here; nothing is copied and every retained file keeps its bytes.
        self.assertEqual(self.inputs(), retained)


@unittest.skipUnless(GIT, "git is not available")
class ShallowCloneTests(GitScratchCase):
    """LAYOUT.md "Validation": depth-1 ``file://`` clones of committed candidates, positive and negative."""

    def setUp(self):
        super().setUp()
        clones = tempfile.TemporaryDirectory()
        self.clones = Path(clones.name)
        self.addCleanup(self.cleanup_clones, clones)

    def cleanup_clones(self, directory):
        make_writable(self.clones)
        directory.cleanup()

    def publish_two_with_a_supersession(self):
        self.write("ADR-015.md", source())
        self.assertTrue(adr.render(self.root, MONEY))
        self.commit("publish ADR-015")
        self.write("ADR-018.md", source(number="ADR-018", ticket=CRYPTO, title="Sample ADR-018", supersedes="ADR-004"))
        self.assertTrue(adr.render(self.root, CRYPTO))
        self.commit("publish ADR-018 superseding ADR-004")
        return {"legacy": 14, "allocations": 9, "published": 2, "pending": 7, "superseded": 1}

    def clone(self, name, branch="main"):
        """``git clone --depth 1 file:///...``: exactly one commit, no parent, a shallow marker."""
        target = self.clones / name
        self.git("clone", "-q", "--depth", "1", "--branch", branch, self.root.as_uri(), str(target))
        self.assertTrue(self.root.as_uri().startswith("file:///"))
        self.assertEqual(self.git("rev-list", "--count", "HEAD", cwd=target).stdout.strip(), "1")
        self.assertNotEqual(self.git("rev-parse", "--verify", "-q", "HEAD^", cwd=target, check=False).returncode, 0)
        self.assertTrue((target / ".git" / "shallow").exists())
        self.assertEqual(
            self.git("rev-parse", "HEAD:adr/presplit-reference.md", cwd=target).stdout.strip(), adr.REFERENCE_BLOB_OID
        )
        return target

    def run_check(self, root):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = adr.main(["check", "--root", str(root)])
        return code, out.getvalue(), err.getvalue()

    def test_depth_one_file_clone_of_a_committed_positive_candidate_validates_without_parent_history(self):
        self.git("branch", "baseline")
        expected = self.publish_two_with_a_supersession()
        self.assertEqual(self.git("rev-list", "--count", "HEAD").stdout.strip(), "3")
        for name, branch, summary in (("baseline", "baseline", BASELINE_SUMMARY), ("positive", "main", expected)):
            with self.subTest(candidate=name):
                clone = self.clone(name, branch)
                self.assertEqual(adr.check_layout(clone), summary)
                code, out, err = self.run_check(clone)
                self.assertEqual((code, err), (0, ""))
                self.assertIn("adr/README.md and adr/accepted-records.json match.", out)
                self.assertEqual(adr.render(clone), [])
                self.assertEqual(self.git("status", "--porcelain", cwd=clone).stdout, "")

    def test_depth_one_file_clone_of_negative_candidates_fails_closed(self):
        self.publish_two_with_a_supersession()
        # Negative A: a hand-edited generated slot, committed.
        self.edit("README.md", "| Date | 2026-10-01 |\n| Supersedes | ADR-004 |", "| Date | 2026-10-02 |\n| Supersedes | ADR-004 |")
        self.commit("hand-edited predecessor slot")
        clone = self.clone("negative-slot")
        with self.assertRaisesRegex(adr.LayoutError, "does not match the rendered layout: generated slot ADR-018 differs"):
            adr.check_layout(clone)
        code, out, err = self.run_check(clone)
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("ERROR: adr/README.md does not match the rendered layout"), err)
        # Negative B: an undated edit of an accepted record with a consistent README; the committed
        # registry is the only baseline the one-commit clone has, and it is enough.
        self.write("README.md", adr.render_readme(adr.validate_sources(self.root)))
        self.edit("ADR-015.md", "Sample text.", "Sample text, quietly changed.")
        self.commit("undated edit of an accepted record")
        clone = self.clone("negative-undated")
        with self.assertRaisesRegex(adr.LayoutError, r"adr/ADR-015\.md: accepted record edited without a date change"):
            adr.check_layout(clone)
        with self.assertRaisesRegex(adr.LayoutError, r"adr/ADR-015\.md: accepted record edited without a date change"):
            adr.render(clone)
        self.assertEqual(self.git("status", "--porcelain", cwd=clone).stdout, "", "a refused render writes nothing")


class Repo:
    """One local git repository under a GitScratchCase's isolated environment."""

    def __init__(self, case, root):
        self.case, self.root, self.adr = case, Path(root), Path(root) / "adr"

    def git(self, *args, check=True):
        return self.case.git(*args, cwd=self.root, check=check)

    def read(self, name):
        return (self.adr / name).read_bytes()

    def squash(self, branch):
        """A plain squash merge, committed: no merge driver, no discarded first squash."""
        self.git("merge", "-q", "--squash", branch)
        self.git("commit", "-q", "-m", f"squash {branch}")


class Branches:
    """The matrix template, built once per module: the baseline committed as ``main`` and one
    ordinary branch per allocation, each publishing its synthetic record with a scoped render."""

    directory = None
    repo = None
    tickets = None
    sources = None

    @classmethod
    def build(cls, case):
        case.init_repo()
        cls.tickets = dict(allocations())
        cls.sources = {}
        for number, ticket in cls.tickets.items():
            case.land(number.lower(), number, ticket)
            cls.sources[number] = case.read(f"{number}.md")
        case.git("checkout", "-q", "main")
        case.assertFalse((case.root / ".gitattributes").exists())
        case.assertNotEqual(case.git("config", "--get-regexp", r"merge\..*\.driver", check=False).returncode, 0)
        cls.directory = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.directory.name) / "repo"
        shutil.copytree(case.root, cls.repo, ignore=shutil.ignore_patterns("home"))

    @classmethod
    def drop(cls):
        if cls.directory is not None:
            make_writable(Path(cls.directory.name))
            cls.directory.cleanup()
            cls.directory = None


def tearDownModule():
    Branches.drop()
    Baseline.directory.cleanup()


@unittest.skipUnless(GIT, "git is not available")
class SquashMergeMatrixTests(GitScratchCase):
    """LAYOUT.md "Validation": nine independent ordinary branches from one split baseline, serially
    squash-merged and committed in forward, reverse and alternating order and in both orders of
    every adjacent pair; strict validation, exact rendering, owner retention and the cumulative
    source set are checked after every merge. Plain ``git merge --squash`` + ``git commit`` only.

    Every sequence starts from a fresh branch cut from ``main`` of a copy of the shared template;
    the copy is reused by the following sequences of the same test (a checkout resets it)."""

    PREPUBLISHED = ()  # numbers landed on main after the branches were cut (a stale-branch landing)
    INIT_REPO = False  # the sequences run on a copy of the shared template, not on self.root

    def setUp(self):
        super().setUp()
        if Branches.directory is None:
            Branches.build(self)
        self.tickets = Branches.tickets
        self.numbers = [number for number in self.tickets if number not in self.PREPUBLISHED]
        self.expected_sources = dict(Branches.sources)
        self.repo = Repo(self, self.root / "matrix")
        shutil.copytree(Branches.repo, self.repo.root)
        for number in self.PREPUBLISHED:
            supersedes = "ADR-004" if number == "ADR-018" else "null"
            record = source(number=number, ticket=self.tickets[number], title=f"Sample {number}", supersedes=supersedes)
            (self.repo.adr / f"{number}.md").write_bytes(record.encode("utf-8"))
            self.assertTrue(adr.render(self.repo.root, self.tickets[number]))
            self.repo.git("add", "-A", "adr")
            self.repo.git("commit", "-q", "-m", f"publish {number} on main")
            self.expected_sources[number] = self.repo.read(f"{number}.md")

    def integrate(self, order, name):
        """Serially squash-merge and commit ``order`` on a fresh branch cut from main."""
        repo = self.repo
        repo.git("checkout", "-q", "-B", name, "main")
        landed = list(self.PREPUBLISHED)
        for number in order:
            repo.squash(number.lower())
            landed.append(number)
            self.assert_layout(repo, landed, f"sequence {name} after {number}")
        return repo.read("README.md"), repo.read("accepted-records.json")

    def integrate_all(self, orders):
        results = {name: self.integrate(order, name) for name, order in orders.items()}
        self.assertEqual(self.repo.git("status", "--porcelain").stdout, "", "every squash merge was committed cleanly")
        return results

    def assert_layout(self, repo, landed, context):
        summary = adr.check_layout(repo.root)  # strict validation: sources, registry, README byte-exact
        self.assertEqual(summary["published"], len(landed), context)
        self.assertEqual(summary["superseded"], int("ADR-018" in self.PREPUBLISHED), context)
        layout = adr.validate_sources(repo.root)
        readme = repo.read("README.md").decode("utf-8")
        self.assertEqual(adr.render_readme(layout).encode("utf-8"), repo.read("README.md"), context)  # exact rendering
        registry = {item["number"]: item for item in json.loads(repo.read("accepted-records.json"))["items"]}
        for number in landed:
            self.assertEqual(repo.read(f"{number}.md"), self.expected_sources[number], f"{context}: {number} source intact")
            allocation = layout.allocations[number]
            self.assertEqual(layout.sources[number].ticket, allocation.ticket, context)  # owner retention
            index, pending = slot_rows(readme, number)
            self.assertEqual((index["Ticket"], pending["Ticket"]), (allocation.ticket, f"`{allocation.ticket}`"), context)
            self.assertIn(f"[{number}.md]({number}.md)", index["Source"], context)
            self.assertEqual(pending["State"], "ACCEPTED", context)
            self.assertEqual(registry[number]["sha256"], layout.sources[number].sha256, context)
        self.assertEqual(  # cumulative source set
            sorted(path.name for path in repo.adr.glob("ADR-*.md")),
            sorted(LEGACY_FILES + [f"{number}.md" for number in landed]), context,
        )
        for number in self.numbers:
            if number not in landed:
                self.assertEqual(slot_rows(readme, number)[0]["Source"], f"reserved for `{self.tickets[number]}`", context)
                self.assertIsNone(registry[number]["date"], context)

    def test_forward_reverse_and_alternating_orders_land_every_branch_into_one_layout(self):
        orders = {"forward": self.numbers, "reverse": self.numbers[::-1], "alternating": alternating(self.numbers)}
        self.assertEqual(len(set(map(tuple, orders.values()))), 3)
        results = self.integrate_all(orders)
        self.assertEqual(len(set(results.values())), 1, "the final README and registry do not depend on the order")
        # The merged layout equals an unscoped render of the same sources placed in one baseline tree.
        root = self.root / "direct"
        shutil.copytree(Baseline.adr, root / "adr")
        for number, data in self.expected_sources.items():
            (root / "adr" / f"{number}.md").write_bytes(data)
        self.assertEqual(adr.render(root), ["adr/README.md", "adr/accepted-records.json"])
        self.assertEqual(results["forward"], ((root / "adr" / "README.md").read_bytes(), (root / "adr" / "accepted-records.json").read_bytes()))

    def test_both_orders_of_every_adjacent_pair_squash_merge_cleanly(self):
        pairs = list(zip(self.numbers, self.numbers[1:]))
        self.assertEqual(len(pairs), len(self.numbers) - 1)
        orders = {}
        for first, second in pairs:
            orders[f"{first}-then-{second}"] = (first, second)
            orders[f"{second}-then-{first}"] = (second, first)
        results = self.integrate_all(orders)
        for first, second in pairs:
            with self.subTest(pair=(first, second)):
                self.assertEqual(results[f"{first}-then-{second}"], results[f"{second}-then-{first}"])


@unittest.skipUnless(GIT, "git is not available")
class SquashMergeMatrixOnPublishedFixtureTests(SquashMergeMatrixTests):
    """The same matrix from a fixture whose main already holds two published records and one
    supersession (ADR-015; ADR-018 superseding ADR-004), landed after the branches were cut; the
    remaining seven branches land on top of them."""

    PREPUBLISHED = ("ADR-015", "ADR-018")


if __name__ == "__main__":
    unittest.main()
