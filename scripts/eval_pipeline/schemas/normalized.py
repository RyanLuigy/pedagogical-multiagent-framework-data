from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Recurso:
    tipo: str
    titulo: str
    minutagem: float
    conteudo_formativo: List[str] = field(default_factory=list)
    objetivos: List[str] = field(default_factory=list)
    id: Optional[str] = None


@dataclass
class UA:
    indice: int
    ua: str
    titulo: str
    conteudo_formativo: List[str] = field(default_factory=list)
    recursos: List[Recurso] = field(default_factory=list)

    @property
    def minutagem_total(self) -> float:
        return sum(r.minutagem for r in self.recursos)

    @property
    def tipos(self) -> List[str]:
        return [r.tipo for r in self.recursos]


@dataclass
class PAA:
    origem: str
    slug: str
    uas: List[UA] = field(default_factory=list)

    @property
    def num_uas(self) -> int:
        return len(self.uas)

    @property
    def num_recursos(self) -> int:
        return sum(len(ua.recursos) for ua in self.uas)

    @property
    def minutagem_total(self) -> float:
        return sum(ua.minutagem_total for ua in self.uas)

    def ua_por_indice(self, indice: int) -> Optional[UA]:
        for ua in self.uas:
            if ua.indice == indice:
                return ua
        return None

    def texto_completo(self) -> str:
        """Serializa o PAA inteiro em texto legível para prompts de LLM."""
        partes = []
        for ua in self.uas:
            partes.append(f"\n## {ua.ua}: {ua.titulo}")
            if ua.conteudo_formativo:
                partes.append("Conteúdo formativo da UA:")
                partes.extend(f"  {c}" for c in ua.conteudo_formativo)
            partes.append("Recursos:")
            for r in ua.recursos:
                partes.append(f"  - [{r.tipo}] {r.titulo} ({r.minutagem} min)")
                if r.objetivos:
                    partes.append(f"    Objetivos: {'; '.join(r.objetivos)}")
                if r.conteudo_formativo:
                    partes.append(f"    Conteúdo formativo: {'; '.join(r.conteudo_formativo)}")
        return "\n".join(partes)
