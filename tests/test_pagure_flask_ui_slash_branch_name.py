# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import tempfile
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import pagure.lib
import tests
from pagure.lib.repo import PagureRepo


class PagureFlaskSlashInBranchtests(tests.Modeltests):
    """ Tests for flask application when the branch name contains a '/'.
    """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(PagureFlaskSlashInBranchtests, self).setUp()

        pagure.APP.config['TESTING'] = True
        pagure.SESSION = self.session
        pagure.lib.SESSION = self.session
        pagure.ui.app.SESSION = self.session
        pagure.ui.filters.SESSION = self.session
        pagure.ui.fork.SESSION = self.session
        pagure.ui.repo.SESSION = self.session

        pagure.APP.config['GIT_FOLDER'] = os.path.join(tests.HERE, 'repos')
        pagure.APP.config['FORK_FOLDER'] = os.path.join(tests.HERE, 'forks')
        pagure.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        pagure.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        pagure.APP.config['REQUESTS_FOLDER'] = os.path.join(
            tests.HERE, 'requests')
        self.app = pagure.APP.test_client()

    def set_up_git_repo(self):
        """ Set up the git repo to play with. """

        # Create a git repo to play with
        gitrepo = os.path.join(tests.HERE, 'repos', 'test.git')
        repo = pygit2.init_repository(gitrepo, bare=True)

        newpath = tempfile.mkdtemp(prefix='pagure-other-test')
        repopath = os.path.join(newpath, 'test')
        clone_repo = pygit2.clone_repository(gitrepo, repopath)

        # Create a file in that git repo
        with open(os.path.join(repopath, 'sources'), 'w') as stream:
            stream.write('foo\n bar')
        clone_repo.index.add('sources')
        clone_repo.index.write()

        # Commits the files added
        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/master',  # the name of the reference to update
            author,
            committer,
            'Add sources file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            []
        )
        refname = 'refs/heads/master'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        master_branch = clone_repo.lookup_branch('master')
        first_commit = master_branch.get_object().hex

        # Second commit
        with open(os.path.join(repopath, '.gitignore'), 'w') as stream:
            stream.write('*~')
        clone_repo.index.add('.gitignore')
        clone_repo.index.write()

        tree = clone_repo.index.write_tree()
        author = pygit2.Signature(
            'Alice Author', 'alice@authors.tld')
        committer = pygit2.Signature(
            'Cecil Committer', 'cecil@committers.tld')
        clone_repo.create_commit(
            'refs/heads/maxamilion/feature',
            author,
            committer,
            'Add .gitignore file for testing',
            # binary string representing the tree object ID
            tree,
            # list of binary strings representing parents of the new commit
            [first_commit]
        )

        refname = 'refs/heads/maxamilion/feature'
        ori_remote = clone_repo.remotes[0]
        PagureRepo.push(ori_remote, refname)

        shutil.rmtree(newpath)

    @patch('pagure.lib.notify.send_email')
    def test_view_repo(self, send_email):
        """ Test the view_repo endpoint when the git repo has no master
        branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<div class="card-block">\n            '
            '<h5><strong>Owners</strong></h5>', output.data)
        self.assertEqual(output.data.count(
            '<a class="dropdown-item" href="/test/branch/maxamilion/feature'),
            1)

    @patch('pagure.lib.notify.send_email')
    def test_view_repo_branch(self, send_email):
        """ Test the view_repo_branch endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/branch/maxamilion/feature')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<div class="card-block">\n            '
            '<h5><strong>Owners</strong></h5>', output.data)
        self.assertEqual(output.data.count(
            '<a class="dropdown-item" href="/test/branch/maxamilion/feature'),
            1)

    @patch('pagure.lib.notify.send_email')
    def test_view_commits(self, send_email):
        """ Test the view_commits endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/commits')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.data.count('<span class="commitdate"'), 1)

        output = self.app.get('/test/commits/maxamilion/feature')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<title>Logs - test - Pagure</title>', output.data)
        self.assertIn('Add sources file for testing', output.data)
        self.assertIn('Add .gitignore file for testing', output.data)
        self.assertEqual(output.data.count('<span class="commitdate"'), 3)

    @patch('pagure.lib.notify.send_email')
    def test_view_file(self, send_email):
        """ Test the view_file endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/blob/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<li><a href="/test/tree/master"><span class="oi" '
            'data-glyph="random"></span>&nbsp; master</a></li>'
            '<li class="active"><span class="oi" data-glyph="file">'
            '</span>&nbsp; sources</li>',
            output.data)

        output = self.app.get('/test/blob/master/f/.gitignore')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/test/blob/maxamilion/feature/f/.gitignore')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<li><a href="/test/tree/maxamilion/feature">'
            '<span class="oi" data-glyph="random"></span>'
            '&nbsp; maxamilion/feature</a></li>'
            '<li class="active"><span class="oi" data-glyph="file">'
            '</span>&nbsp; .gitignore</li>',
            output.data)
        self.assertIn('<td class="cell2"><pre>*~</pre></td>', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_view_raw_file(self, send_email):
        """ Test the view_raw_file endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/raw/master/f/sources')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/raw/master')
        self.assertEqual(output.status_code, 200)
        self.assertIn('diff --git a/sources b/sources', output.data)
        self.assertIn('+foo\n+ bar', output.data)
        output = self.app.get('/test/raw/master/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertEqual(output.data, 'foo\n bar')

        output = self.app.get('/test/raw/maxamilion/feature')
        self.assertEqual(output.status_code, 200)
        self.assertIn('diff --git a/.gitignore b/.gitignore', output.data)
        self.assertIn('+*~', output.data)

        output = self.app.get('/test/raw/maxamilion/feature/f/sources')
        self.assertEqual(output.status_code, 200)
        self.assertEqual('foo\n bar', output.data)

    @patch('pagure.lib.notify.send_email')
    def test_view_tree(self, send_email):
        """ Test the view_tree endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/tree/')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/tree/master')
        self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        # With git repo
        output = self.app.get('/test/tree/master')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<a href="/test/blob/master/f/sources">', output.data)
        self.assertEqual(
            output.data.count('<span class="oi text-muted" data-glyph="file">'), 1)

        output = self.app.get('/test/tree/master/sources')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<a href="/test/blob/master/f/sources">', output.data)
        self.assertEqual(
            output.data.count('<span class="oi text-muted" data-glyph="file">'), 1)

        output = self.app.get('/test/tree/feature')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<a href="/test/blob/master/f/sources">', output.data)
        self.assertIn(
            '<td class-"pagure-table-filehex">\n'
            '                            9f4435', output.data)
        self.assertEqual(
            output.data.count('<span class="oi text-muted" data-glyph="file">'), 1)

        output = self.app.get('/test/tree/maxamilion/feature')
        self.assertEqual(output.status_code, 200)
        self.assertIn(
            '<a href="/test/blob/maxamilion/feature/f/sources">',
            output.data)
        self.assertIn(
            '<td class-"pagure-table-filehex">\n'
            '                            9f4435', output.data)
        self.assertIn(
            '<td class-"pagure-table-filehex">\n'
            '                            e4e5f6', output.data)
        self.assertEqual(
            output.data.count('<span class="oi text-muted" data-glyph="file">'), 2)

        # Wrong identifier, back onto master
        output = self.app.get('/test/tree/maxamilion/feature/f/.gitignore')
        self.assertEqual(output.status_code, 200)
        self.assertIn('<a href="/test/blob/master/f/sources">', output.data)
        self.assertIn(
            '<td class-"pagure-table-filehex">\n'
            '                            9f4435', output.data)
        self.assertEqual(
            output.data.count('<span class="oi text-muted" data-glyph="file">'), 1)

    @patch('pagure.lib.notify.send_email')
    def test_new_request_pull(self, send_email):
        """ Test the new_request_pull endpoint when the git repo has no
        master branch.
        """
        send_email.return_value = True

        tests.create_projects(self.session)
        # Non-existant git repo
        output = self.app.get('/test/diff/master..maxamilion/feature')
        # (used to be 302 but seeing a diff is allowed even logged out)
        self.assertEqual(output.status_code, 404)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/diff/master..maxamilion/feature')
            self.assertEqual(output.status_code, 404)

        self.set_up_git_repo()

        output = self.app.get('/test/diff/master..maxamilion/feature')
        # (used to be 302 but seeing a diff is allowed even logged out)
        self.assertEqual(output.status_code, 200)
        self.assertEqual(
            output.data.count('<span class="commitdate" title='), 1)
        self.assertIn('<h5>.gitignore', output.data)

        user = tests.FakeUser()
        with tests.user_set(pagure.APP, user):
            output = self.app.get('/test/diff/master..maxamilion/feature')
            self.assertEqual(output.status_code, 200)
            self.assertEqual(
                output.data.count('<span class="commitdate" title='), 1)
            self.assertIn('<h5>.gitignore', output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(
        PagureFlaskSlashInBranchtests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
