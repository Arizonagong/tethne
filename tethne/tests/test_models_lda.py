import sys
sys.path.append('../tethne')

import unittest
import tempfile
import os
from xml.etree import ElementTree as ET
import networkx as nx
import csv


from tethne.readers.wos import read
from tethne import FeatureSet, tokenize
from tethne.networks import topics, features

datapath = './tethne/tests/data/wos3.txt'

import logging
logger = logging.getLogger('mallet')
logger.setLevel('DEBUG')


class TestHelpers(unittest.TestCase):
    def test_mallet_to_theta_featureset(self):
        from tethne import mallet_to_theta_featureset
        theta = mallet_to_theta_featureset('tethne/tests/data/mallet/dt.dat')
        self.assertIsInstance(theta, FeatureSet)
        self.assertEqual(len(theta), 220, 'there should be 220 documents')

        graph = features.feature_cooccurrence(theta, 'theta', 0.05)
        self.assertIsInstance(graph, nx.Graph)

    def test_mallet_to_theta_featureset_noname(self):
        from tethne import mallet_to_theta_featureset
        theta = mallet_to_theta_featureset('tethne/tests/data/mallet/dt_noname.dat')
        self.assertIsInstance(theta, FeatureSet)
        self.assertEqual(len(theta), 220, 'there should be 220 documents')

        graph = features.feature_cooccurrence(theta, 'theta', 0.05)
        self.assertIsInstance(graph, nx.Graph)

    def test_mallet_to_phi_featureset(self):
        from tethne import mallet_to_phi_featureset
        phi, vocab = mallet_to_phi_featureset('tethne/tests/data/mallet/wt.dat')
        self.assertIsInstance(phi, FeatureSet)
        self.assertEqual(len(phi), 20)

    # TODO: Fix this test (TETHNE-147)
    # def test_mallet_to_theta_featureset_tab(self):
    #     from tethne import mallet_to_theta_featureset
    #     theta = mallet_to_theta_featureset('tethne/tests/data/mallet/tutorial_doc_topic.txt')
    #     self.assertIsInstance(theta, FeatureSet)


class TestLDAModelExistingOutput(unittest.TestCase):
    def setUp(self):
        from tethne.model.corpus.mallet import LDAModel
        self.corpus = read(datapath, index_by='wosid')
        self.corpus.index_feature('abstract', tokenize, structured=True)
        self.old_model = LDAModel(self.corpus, featureset_name='abstract', nodelete=True)
        self.old_model.fit(Z=20, max_iter=50)

    def test_load_existing_data(self):
        from tethne.model.corpus.mallet import LDAModel
        new_model = LDAModel(self.corpus, featureset_name='abstract',
                             nodelete=True,
                             prep=False,
                             wt=self.old_model.wt,
                             dt=self.old_model.dt,
                             om=self.old_model.om)
        new_model.load()

        self.assertEqual(self.old_model.topics_in(u'WOS:000295037200001'),
                         new_model.topics_in(u'WOS:000295037200001'))

    def test_load_existing_data_staticmethod(self):
        from tethne.model.corpus.mallet import LDAModel
        new_model = LDAModel.from_mallet(self.old_model.wt,
                                         self.old_model.dt,
                                         self.old_model.om)

        self.assertEqual(self.old_model.topics_in(u'WOS:000295037200001'),
                         new_model.topics_in(u'WOS:000295037200001'))

        self.assertTrue(hasattr(new_model, 'Z'))

        from tethne import topic_coupling
        graph = topic_coupling(new_model)


class TestLDAModel(unittest.TestCase):
    def setUp(self):
        from tethne.model.corpus.mallet import LDAModel
        corpus = read(datapath, index_by='wosid')
        corpus.index_feature('abstract', tokenize, structured=True)
        self.model = LDAModel(corpus, featureset_name='abstract')
        self.model.fit(Z=20, max_iter=500)

    def test_ldamodel(self):
        dates, rep = self.model.topic_over_time(1)
        self.assertGreater(sum(rep), 0)
        self.assertEqual(len(dates), len(rep))

        self.assertIsInstance(self.model.phi, FeatureSet)
        self.assertIsInstance(self.model.theta, FeatureSet)

        self.assertIsInstance(self.model.list_topics(), list)
        self.assertGreater(len(self.model.list_topics()), 0)
        self.assertIsInstance(self.model.list_topic(0), list)
        self.assertGreater(len(self.model.list_topic(0)), 0)

    def test_networks(self):
        termGraph = topics.terms(self.model)
        self.assertGreater(termGraph.size(), 100)
        self.assertGreater(termGraph.order(), 10)

        topicGraph = topics.cotopics(self.model)
        self.assertGreater(topicGraph.size(), 5)
        self.assertGreater(topicGraph.order(), 0)

        paperGraph = topics.topic_coupling(self.model)
        self.assertGreater(paperGraph.size(), 100)
        self.assertGreater(paperGraph.order(), 20)


class TestLDAModelUnstructured(unittest.TestCase):
    def setUp(self):
        from tethne.model.corpus.mallet import LDAModel
        corpus = read(datapath, index_by='wosid')
        corpus.index_feature('abstract', tokenize)
        self.model = LDAModel(corpus, featureset_name='abstract')
        self.model.fit(Z=20, max_iter=500)

    def test_ldamodel(self):
        dates, rep = self.model.topic_over_time(1)
        self.assertGreater(sum(rep), 0)
        self.assertEqual(len(dates), len(rep))

        self.assertIsInstance(self.model.phi, FeatureSet)
        self.assertIsInstance(self.model.theta, FeatureSet)

        self.assertIsInstance(self.model.list_topics(), list)
        self.assertGreater(len(self.model.list_topics()), 0)
        self.assertIsInstance(self.model.list_topic(0), list)
        self.assertGreater(len(self.model.list_topic(0)), 0)

    def test_networks(self):
        termGraph = topics.terms(self.model)
        self.assertGreater(termGraph.size(), 100)
        self.assertGreater(termGraph.order(), 10)

        topicGraph = topics.cotopics(self.model)
        self.assertGreater(topicGraph.size(), 5)
        self.assertGreater(topicGraph.order(), 0)

        paperGraph = topics.topic_coupling(self.model)
        self.assertGreater(paperGraph.size(), 100)
        self.assertGreater(paperGraph.order(), 20)


class TestLDAModelWithTransformation(unittest.TestCase):
    def setUp(self):
        from tethne.model.corpus.mallet import LDAModel
        corpus = read(datapath, index_by='wosid')
        corpus.index_feature('abstract', tokenize)

        xf = lambda f, c, C, DC: c*3
        corpus.features['xf'] = corpus.features['abstract'].transform(xf)
        self.model = LDAModel(corpus, featureset_name='xf')
        self.model.fit(Z=20, max_iter=500)

    def test_ldamodel(self):
        dates, rep = self.model.topic_over_time(1)
        self.assertGreater(sum(rep), 0)
        self.assertEqual(len(dates), len(rep))

        self.assertIsInstance(self.model.phi, FeatureSet)
        self.assertIsInstance(self.model.theta, FeatureSet)

        self.assertIsInstance(self.model.list_topics(), list)
        self.assertGreater(len(self.model.list_topics()), 0)
        self.assertIsInstance(self.model.list_topic(0), list)
        self.assertGreater(len(self.model.list_topic(0)), 0)

    def test_networks(self):
        termGraph = topics.terms(self.model)
        self.assertGreater(termGraph.size(), 100)
        self.assertGreater(termGraph.order(), 10)

        topicGraph = topics.cotopics(self.model)
        self.assertGreater(topicGraph.size(), 5)
        self.assertGreater(topicGraph.order(), 0)

        paperGraph = topics.topic_coupling(self.model)
        self.assertGreater(paperGraph.size(), 100)
        self.assertGreater(paperGraph.order(), 20)


class TestLDAModelMALLETPath(unittest.TestCase):
    def test_direct_import(self):
        from tethne import LDAModel
        corpus = read(datapath, index_by='wosid')
        corpus.index_feature('abstract', tokenize, structured=True)
        self.model = LDAModel(corpus, featureset_name='abstract')
        self.model.fit(Z=20, max_iter=500)


if __name__ == '__main__':
    unittest.main()
