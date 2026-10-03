"""Popula o banco com dados sintéticos.

Uso (dentro do container):
    python -m scripts.seed           # não faz nada se já houver dados
    python -m scripts.seed --reset   # apaga tudo e recria

Todos os dados são criados através dos services: respeitam as regras de negócio
e geram a trilha de auditoria, exatamente como se tivessem vindo da API.
As datas são relativas a hoje, para que "vencido" continue fazendo sentido.

Além de ~40 títulos "normais", cria cenários propositalmente problemáticos
(números NF-9xxx), que serão usados pelo Copilot nas próximas fases.
"""

import argparse
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core import cnpj
from app.core.db import SessionLocal
from app.models import CentroCusto, Fornecedor, TituloPagar
from app.models.types import CENTAVOS
from app.schemas.centro_custo import CentroCustoCreate, CentroCustoUpdate
from app.schemas.fornecedor import FornecedorCreate, FornecedorUpdate
from app.schemas.pagamento import PagamentoCreate
from app.schemas.rateio import RateioCreate
from app.schemas.titulo import TituloCreate
from app.services.centro_custo_service import CentroCustoService
from app.services.fornecedor_service import FornecedorService
from app.services.pagamento_service import PagamentoService
from app.services.rateio_service import RateioService
from app.services.titulo_service import TituloService

HOJE = date.today()
rng = random.Random(42)  # determinístico: o mesmo seed gera os mesmos dados

FORNECEDORES = [
    "Alfa Tecnologia Ltda",
    "Beta Serviços de Limpeza S.A.",
    "Construtora Horizonte Ltda",
    "Delta Logística e Transportes",
    "Energia Sul Distribuidora",
    "Folha Branca Papelaria",
    "Gama Consultoria Empresarial",
    "Hiper Telecom S.A.",
    "Ícaro Segurança Patrimonial",
    "Gráfica Antiga Ltda",  # será inativado
]

CENTROS_CUSTO = [
    ("1001", "Financeiro"),
    ("1002", "Tecnologia da Informação"),
    ("1003", "Recursos Humanos"),
    ("1004", "Comercial"),
    ("1005", "Marketing"),
    ("1006", "Operações"),
    ("1007", "Logística"),
    ("1008", "Jurídico"),
    ("1009", "Facilities"),
    ("1010", "Projetos Descontinuados"),  # será inativado
]

DESCRICOES = [
    "Licenças de software",
    "Serviço de limpeza mensal",
    "Manutenção predial",
    "Frete de mercadorias",
    "Conta de energia elétrica",
    "Material de escritório",
    "Consultoria tributária",
    "Link de internet dedicado",
    "Vigilância patrimonial",
    "Impressão de materiais",
]


class Seeder:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.fornecedores = FornecedorService(db)
        self.centros = CentroCustoService(db)
        self.titulos = TituloService(db)
        self.rateios = RateioService(db)
        self.pagamentos = PagamentoService(db)

    # ------------------------------------------------------------- helpers

    def titulo(
        self,
        numero: str,
        fornecedor: Fornecedor,
        valor: Decimal,
        emissao: date,
        vencimento: date,
        descricao: str | None = None,
    ) -> TituloPagar:
        return self.titulos.criar(
            TituloCreate(
                numero=numero,
                fornecedor_id=fornecedor.id,
                descricao=descricao or rng.choice(DESCRICOES),
                data_emissao=emissao,
                data_vencimento=vencimento,
                valor_total=valor,
            )
        )

    def ratear(self, titulo: TituloPagar, partes: list[tuple[CentroCusto, Decimal]]) -> None:
        for centro, valor in partes:
            self.rateios.adicionar(titulo.id, RateioCreate(centro_custo_id=centro.id, valor=valor))

    def ratear_integral(self, titulo: TituloPagar, centros: list[CentroCusto]) -> None:
        """Divide o valor do título entre 1 a 3 centros, fechando exatamente 100%."""
        escolhidos = rng.sample(centros, k=rng.randint(1, 3))
        pesos = [rng.randint(1, 10) for _ in escolhidos]
        partes, restante = [], titulo.valor_total
        for centro, peso in zip(escolhidos[:-1], pesos[:-1], strict=True):
            valor = (titulo.valor_total * peso / sum(pesos)).quantize(CENTAVOS)
            partes.append((centro, valor))
            restante -= valor
        partes.append((escolhidos[-1], restante))
        self.ratear(titulo, partes)

    def pagar(self, titulo: TituloPagar, valor: Decimal) -> None:
        limite = min(HOJE, titulo.data_vencimento)
        dias = max((limite - titulo.data_emissao).days, 0)
        data = titulo.data_emissao + timedelta(days=rng.randint(0, dias))
        self.pagamentos.registrar(titulo.id, PagamentoCreate(data_pagamento=data, valor=valor))

    # ------------------------------------------------------------- execução

    def run(self) -> None:
        fornecedores = [
            self.fornecedores.criar(FornecedorCreate(nome=nome, cnpj=cnpj.gerar(10_000 + i)))
            for i, nome in enumerate(FORNECEDORES, start=1)
        ]
        centros = [
            self.centros.criar(CentroCustoCreate(codigo=codigo, descricao=descricao))
            for codigo, descricao in CENTROS_CUSTO
        ]
        cc = {c.codigo: c for c in centros}
        fornecedor_inativo = fornecedores[-1]
        centro_inativo = cc["1010"]

        self.cenarios_problematicos(fornecedores, cc, fornecedor_inativo, centro_inativo)

        # Inativações acontecem DEPOIS dos lançamentos antigos: o histórico permanece,
        # mas novos títulos/rateios passam a ser bloqueados (regras 3 e 4).
        self.fornecedores.atualizar(
            fornecedor_inativo.id, FornecedorUpdate(nome=fornecedor_inativo.nome, ativo=False)
        )
        self.centros.atualizar(
            centro_inativo.id,
            CentroCustoUpdate(descricao=centro_inativo.descricao, ativo=False),
        )

        self.titulos_normais(fornecedores[:-1], [c for c in centros if c is not centro_inativo])

    def cenarios_problematicos(
        self,
        fornecedores: list[Fornecedor],
        cc: dict[str, CentroCusto],
        fornecedor_inativo: Fornecedor,
        centro_inativo: CentroCusto,
    ) -> None:
        f = fornecedores
        d = timedelta

        # Vencido: aprovado, nada pago, vencimento há 12 dias.
        t = self.titulo("NF-9001", f[0], Decimal("4800.00"), HOJE - d(42), HOJE - d(12))
        self.ratear(t, [(cc["1002"], Decimal("4800.00"))])
        self.titulos.aprovar(t.id)

        # Sem rateio: não pode ser aprovado.
        self.titulo("NF-9002", f[1], Decimal("2350.00"), HOJE - d(5), HOJE + d(25))

        # Parcialmente rateado: 60% rateado, aprovação bloqueada.
        t = self.titulo("NF-9003", f[2], Decimal("10000.00"), HOJE - d(10), HOJE + d(20))
        self.ratear(t, [(cc["1006"], Decimal("4000.00")), (cc["1009"], Decimal("2000.00"))])

        # Erro de integração: centro de custo não existe no ERP de destino.
        t = self.titulo("NF-9004", f[3], Decimal("1575.90"), HOJE - d(8), HOJE + d(7))
        self.ratear(t, [(cc["1001"], Decimal("1575.90"))])
        self.titulos.aprovar(t.id)
        self.titulos.registrar_erro_integracao(
            t.id,
            "Integração ERP rejeitou o título: centro de custo 1001 inexistente no ERP de destino.",
        )

        # Erro de integração: fornecedor não cadastrado no ERP.
        t = self.titulo("NF-9005", f[4], Decimal("890.00"), HOJE - d(3), HOJE + d(27))
        self.ratear(t, [(cc["1009"], Decimal("890.00"))])
        self.titulos.registrar_erro_integracao(
            t.id,
            f"Integração ERP rejeitou o título: fornecedor CNPJ {f[4].cnpj} "
            "não cadastrado no ERP de destino.",
        )

        # Título de fornecedor que será inativado (criado antes da inativação).
        t = self.titulo(
            "NF-9006", fornecedor_inativo, Decimal("640.00"), HOJE - d(20), HOJE + d(10)
        )
        self.ratear(t, [(cc["1005"], Decimal("640.00"))])

        # Rateio em centro de custo que será inativado.
        t = self.titulo("NF-9007", f[5], Decimal("1200.00"), HOJE - d(15), HOJE + d(15))
        self.ratear(t, [(centro_inativo, Decimal("700.00")), (cc["1004"], Decimal("500.00"))])

        # Parcialmente pago.
        t = self.titulo("NF-9008", f[6], Decimal("3000.00"), HOJE - d(20), HOJE + d(10))
        self.ratear(t, [(cc["1008"], Decimal("3000.00"))])
        self.titulos.aprovar(t.id)
        self.pagar(t, Decimal("1200.00"))

        # Completamente pago (em duas parcelas).
        t = self.titulo("NF-9009", f[7], Decimal("2500.00"), HOJE - d(40), HOJE - d(10))
        self.ratear(t, [(cc["1002"], Decimal("1500.00")), (cc["1004"], Decimal("1000.00"))])
        self.titulos.aprovar(t.id)
        self.pagar(t, Decimal("1000.00"))
        self.pagar(t, Decimal("1500.00"))

        # Cancelado.
        t = self.titulo("NF-9010", f[8], Decimal("450.00"), HOJE - d(12), HOJE + d(18))
        self.titulos.cancelar(t.id, "Nota fiscal emitida em duplicidade pelo fornecedor")

        # Vencido e parcialmente pago.
        t = self.titulo("NF-9011", f[0], Decimal("7200.00"), HOJE - d(50), HOJE - d(20))
        self.ratear(t, [(cc["1006"], Decimal("7200.00"))])
        self.titulos.aprovar(t.id)
        self.pagar(t, Decimal("3600.00"))

    def titulos_normais(self, fornecedores: list[Fornecedor], centros: list[CentroCusto]) -> None:
        destinos = ["PAGO"] * 14 + ["APROVADO"] * 10 + ["PARCIAL"] * 4 + ["PENDENTE"] * 9
        destinos += ["CANCELADO"] * 2
        rng.shuffle(destinos)

        for i, destino in enumerate(destinos, start=1):
            emissao = HOJE - timedelta(days=rng.randint(0, 90))
            vencimento = emissao + timedelta(days=rng.choice([15, 28, 30, 45, 60]))
            valor = Decimal(rng.randint(15_000, 2_500_000)) / 100
            t = self.titulo(f"NF-{i:04d}", rng.choice(fornecedores), valor, emissao, vencimento)

            if destino == "CANCELADO":
                self.titulos.cancelar(t.id, "Serviço não prestado")
                continue
            self.ratear_integral(t, centros)
            if destino == "PENDENTE":
                continue
            self.titulos.aprovar(t.id)
            if destino == "PAGO":
                self.pagar(t, t.valor_total)
            elif destino == "PARCIAL":
                self.pagar(t, (t.valor_total / 2).quantize(CENTAVOS))


def reset(db: Session) -> None:
    db.execute(
        text(
            "TRUNCATE logs_auditoria, pagamentos, rateios_titulo, titulos_pagar, "
            "centros_custo, fornecedores RESTART IDENTITY CASCADE"
        )
    )
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="apaga todos os dados antes")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            reset(db)
        elif db.scalar(select(func.count()).select_from(Fornecedor)):
            print("Banco já possui dados. Use --reset para recriar.")
            return

        Seeder(db).run()

        por_status = db.execute(
            select(TituloPagar.status, func.count()).group_by(TituloPagar.status)
        ).all()
        print("Seed concluído. Títulos por status:")
        for status, total in sorted(por_status):
            print(f"  {status:<10} {total}")


if __name__ == "__main__":
    main()
