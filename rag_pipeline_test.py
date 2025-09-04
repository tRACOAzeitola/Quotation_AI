"""
Simulação de pipeline RAG local com e-mails/cotações fictícios.
- Persiste ChromaDB em ./rag_test_db
- Ingere 5 exemplos simulados
- Executa consultas de demonstração e imprime os resultados relevantes

Execução:
    python3 rag_pipeline_test.py
"""
from __future__ import annotations

from rag_store import RagStore


def load_fixtures():
    # 5 e-mails/cotações fictícios (texto + metadata associada)
    # Observação: em produção, o texto poderia ser o corpo do e-mail completo.
    fixtures = [
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
        (
            "Entrega aeroporto: Aeroporto de Lisboa a/c JTM. Peso 190 kg. Dimensões 112x47x80 cm.",
            {"destino": "lisboa", "peso": 190, "volume": 0.42, "temperatura": "ambiente", "fonte": "email"},
        ),
        (
            "Entrega : Albufeira. Peso 2t. Dimensões 3 x 3 x 5 cm. fruta",
            {"destino": "portimão", "peso": 2000, "volume": 45, "temperatura": "frio", "fonte": "email"},
        ),
    (
    """Pedido: Bom dia Ricardo,
Por favor, confirmem valor e disponibilidade para a recolha abaixo:
Morada da Recolha:
Mesclachoice
Casal do Troca
Estrada da Paiã
1675-076 Pontinha
Data de Recolha: 02/09 às 14h30
Carga:
Qty: 1 plt
Dms: 112x47x80 cm
Wght: 190 kg
Entrega:
Aeroporto de Lisboa a/c JTM
Destino - LIS / HAV - CUBA
Entregar na Portway
Obrigada""",
    {"destino": "lisboa", "peso": 190, "volume": 0.42, "temperatura": "ambiente", "fonte": "email"}
)
    
    ]
    return fixtures


def main():
    store = RagStore(persist_path="./rag_test_db")

    # Ingestão de fixtures
    print("--- Ingestão de e-mails/cotações fictícios ---")
    for text, meta in load_fixtures():
        doc_id = store.ingest_email(text, meta)
        print(f"Ingerido doc_id={doc_id} | destino={meta.get('destino')} | resumo='{text[:60]}...'")

    # Consultas de exemplo
    queries = [
        "Palmela aeroporto entrega",  # espera recuperar casos de Lisboa/Setúbal relacionados a aeroporto
        "transporte frio para Porto 100 kg 40 m3",
        "Leiria carga 30 m3 frio",
    ]

    print("\n--- Consultas de exemplo ---")
    for q in queries:
        print(f"\n[Query] {q}")
        results = store.retrieve_similar(q, top_k=3)
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            score = r.get('score')
            score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
            print(
                f" {i}. score={score_str} destino={meta.get('destino')} temperatura={meta.get('temperatura')} texto='{r.get('text', '')[:80]}...'"
            )


if __name__ == "__main__":
    main()
