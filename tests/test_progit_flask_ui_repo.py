# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import json
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitFlaskRepotests(tests.Modeltests):
    """ Tests for flask app controller of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskRepotests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.ui.SESSION = self.session
        progit.ui.app.SESSION = self.session
        progit.ui.repo.SESSION = self.session

        progit.APP.config['GIT_FOLDER'] = tests.HERE
        progit.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        progit.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        progit.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = progit.APP.test_client()

    def test_add_user(self):
        """ Test the add_user endpoint. """

        output = self.app.get('/foo/adduser')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/foo/adduser')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'user': 'ralph',
            }

            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<li class="error">No user &#34;ralph&#34; found</li>'
                in output.data)

            data['user'] = 'foo'
            output = self.app.post(
                '/test/adduser', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">User added</li>' in output.data)

    def test_remove_user(self):
        """ Test the remove_user endpoint. """

        output = self.app.post('/foo/dropuser/1')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.post('/foo/dropuser/1')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/dropuser/1')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.post('/test/settings')

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="error">User does not have commit or cannot '
                'loose it right</li>' in output.data)

        # Add an user to a project
        repo = progit.lib.get_project(self.session, 'test')
        msg = progit.lib.add_user_to_project(
            session=self.session,
            project=repo,
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        with tests.user_set(progit.APP, user):
            output = self.app.post('/test/dropuser/2', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertFalse(
                '<li class="message">User removed</li>' in output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">User removed</li>' in output.data)

    def test_update_description(self):
        """ Test the update_description endpoint. """
        output = self.app.post('/foo/updatedesc')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.post('/foo/updatedesc')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/updatedesc')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.post('/test/updatedesc', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'new description for test project #1',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/updatedesc', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">Description updated</li>'
                in output.data)

    def test_view_settings(self):
        """ Test the view_settings endpoint. """
        output = self.app.get('/foo/settings')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/foo/settings')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(tests.HERE)

            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            # Both checkbox checked before
            self.assertTrue(
                '<input checked id="project_docs" name="project_docs" '
                'type="checkbox" value="y">' in output.data)
            self.assertTrue(
                '<input checked id="issue_tracker" name="issue_tracker" '
                'type="checkbox" value="y">' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            # Both checkbox are still checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertTrue(
                '<input checked id="project_docs" name="project_docs" '
                'type="checkbox" value="y">' in output.data)
            self.assertTrue(
                '<input checked id="issue_tracker" name="issue_tracker" '
                'type="checkbox" value="y">' in output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<title>Overview - test - ProGit</title>' in output.data)
            self.assertTrue(
                '<li class="message">Edited successfully settings of '
                'repo: test</li>' in output.data)

            # Both checkbox are now un-checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertTrue(
                '<input id="project_docs" name="project_docs" '
                'type="checkbox" value="y">' in output.data)
            self.assertTrue(
                '<input id="issue_tracker" name="issue_tracker" '
                'type="checkbox" value="y">' in output.data)

    def test_view_forks(self):
        """ Test the view_forks endpoint. """

        output = self.app.get('/foo/forks')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/forks')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('This project has not been forked.' in output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskRepotests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
