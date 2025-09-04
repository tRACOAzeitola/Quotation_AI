import os
import shutil
import unittest

from rag_store import RagStore


class TestRagPipeline(unittest.TestCase):
    def setUp(self):
        # Use a separate test DB path to avoid clobbering the main rag_test_db
        self.test_db_path = "./rag_test_db_test"
        if os.path.exists(self.test_db_path):
            shutil.rmtree(self.test_db_path)
        os.makedirs(self.test_db_path, exist_ok=True)
        self.store = RagStore(persist_path=self.test_db_path)

        # Ingest fixtures
        self.fixtures = [
            (
                "Pedido: transporte 900 kg e 30 m3 para Leiria, carga fria, recolha em Coimbra.",
                {"destino": "leiria", "peso": 900, "volume": 30.0, "temperatura": "frio", "fonte": "email"},
            ),
            (
                "Cotação anterior: Aeroporto de Lisboa, 0.5 m3, 120 kg, ambiente. Cliente JTM.",
                {"destino": "lisboa", "peso": 120, "volume": 0.5, "temperatura": "ambiente", "fonte": "cotacao"},
            ),
            (
                "Re: Transporte para Porto, 100 kg, 40 m3, frio. Camiao Grande requerido.",
                {"destino": "porto", "peso": 100, "volume": 40.0, "temperatura": "frio", "fonte": "email"},
            ),
            (
                "Solicitação: 1500 kg, 3x3x5 metros (45 m3) para Setubal. Temperatura ambiente.",
                {"destino": "setubal", "peso": 1500, "volume": 45.0, "temperatura": "ambiente", "fonte": "email"},
            ),
        ]

        for text, meta in self.fixtures:
            self.store.ingest_email(text, meta)

    def tearDown(self):
        # Cleanup database directory
        if os.path.exists(self.test_db_path):
            shutil.rmtree(self.test_db_path)

    def test_query_retrieves_relevant_examples_porto(self):
        results = self.store.retrieve_similar("transporte frio para Porto 100 kg 40 m3", top_k=3)
        self.assertTrue(len(results) >= 1)
        top_meta = results[0].get("metadata", {})
        self.assertIn(top_meta.get("destino"), {"porto"})

    def test_query_retrieves_relevant_examples_aeroporto(self):
        results = self.store.retrieve_similar("Palmela aeroporto entrega", top_k=3)
        self.assertTrue(len(results) >= 1)
        # Aceita Lisboa/Setubal como relevantes
        destinos = {r.get("metadata", {}).get("destino") for r in results}
        self.assertTrue(len(destinos.intersection({"lisboa", "setubal"})) >= 1)

    def test_query_retrieves_relevant_examples_leiria(self):
        results = self.store.retrieve_similar("Leiria carga 30 m3 frio", top_k=3)
        self.assertTrue(len(results) >= 1)
        destinos = {r.get("metadata", {}).get("destino") for r in results}
        self.assertIn("leiria", destinos)


if __name__ == "__main__":
    unittest.main()
