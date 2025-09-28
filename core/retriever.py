import re
import logging
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document
from langchain_mongodb.vectorstores import MongoDBAtlasVectorSearch

from config.settings import settings
from config.constants import ARTICLE_PATTERNS, CATEGORY_KEYWORDS, DOCUMENT_TYPE_KEYWORDS

logger = logging.getLogger(__name__)

class LegalRetriever:
    def __init__(self, vectorstore: MongoDBAtlasVectorSearch, collection):
        self.vectorstore = vectorstore
        self.collection = collection

    def smart_legal_query(self, user_query: str, country: str) -> Tuple[List[Document], List[str], Dict[str, Any], str]:
        """Perform smart legal search with automatic fallback and custom messages"""
        # Détection initiale du type de document
        initial_doc_type = self._detect_document_type(user_query.lower())
        pre_filter = self._build_pre_filters(user_query, country)
        
        logger.info(f"📋 Filtre doc_type initial: {initial_doc_type}")
        logger.info(f"🔍 Recherche {country} avec filtres: {pre_filter}")
        
        # Première recherche
        enhanced_docs, detected_articles, applied_filters = self._perform_search(
            user_query, country, pre_filter
        )
        
        message_supplementaire = ""
        
        # Fallback automatique si aucun résultat pour case_study
        if not enhanced_docs and initial_doc_type == "case_study":
            logger.info("🔄 Fallback: Aucun case_study trouvé, recherche dans les articles")
            pre_filter["doc_type"] = "articles"
            pre_filter["fallback_used"] = True
            
            enhanced_docs, detected_articles, applied_filters = self._perform_search(
                user_query, country, pre_filter
            )
            applied_filters["original_search"] = "case_study"
            applied_filters["fallback_to"] = "articles"
            
            # Message personnalisé pour le fallback
            message_supplementaire = "La base sera enrichie avec des décisions de justice prochainement."
        
        return enhanced_docs, detected_articles, applied_filters, message_supplementaire

    def _perform_search(self, user_query: str, country: str, pre_filter: Dict) -> Tuple[List[Document], List[str], Dict[str, Any]]:
        """Effectue la recherche avec les filtres donnés"""
        detected_articles = self._detect_articles(user_query)
        enhanced_query = self._enhance_query(user_query, detected_articles)
        
        logger.info(f"🔢 Articles détectés: {detected_articles}")
        logger.info(f"📝 Requête enrichie: {enhanced_query[:100]}...")
        
        docs = self.vectorstore.similarity_search(
            enhanced_query, 
            k=settings.MAX_SEARCH_RESULTS, 
            pre_filter=pre_filter
        )
        
        enhanced_docs = self.enhance_with_article_context(docs)
        return enhanced_docs, detected_articles, pre_filter

    def _build_pre_filters(self, query: str, country: str) -> Dict[str, Any]:
        """Build search filters based on query and country"""
        # Filtre pays obligatoire
        pre_filter = {"pays": "Bénin" if country == "benin" else "Madagascar"}
        
        # Filtre doc_type pour différencier articles et études de cas
        query_lower = query.lower()
        pre_filter["doc_type"] = self._detect_document_type(query_lower)
        
        # Filtres par catégorie (optionnels)
        for keyword, category in CATEGORY_KEYWORDS.items():
            if keyword in query_lower:
                pre_filter["categorie"] = category
                logger.info(f"🏷️ Filtre catégorie: {category}")
                break
                
        return pre_filter

    def _detect_document_type(self, query_lower: str) -> str:
        """Détecte le type de document basé sur les mots-clés de la requête"""
        # Mots-clés pour les études de cas
        case_study_indicators = [
            "jurisprudence", "arrêt", "décision", "tribunal", "cours", "jugement",
            "affaire", "procès", "litige", "contentieux", "précédent", "cas",
            "cour d'appel", "cour suprême", "conseil d'état", "juridiction"
        ]
        
        # Mots-clés pour les articles
        articles_indicators = [
            "article", "loi", "code", "décret", "texte", "disposition",
            "règlement", "ordonnance", "prescription", "norme", "chapitre", "titre"
        ]
        
        case_study_score = sum(1 for keyword in case_study_indicators if keyword in query_lower)
        articles_score = sum(1 for keyword in articles_indicators if keyword in query_lower)
        
        if case_study_score > articles_score and case_study_score > 0:
            return "case_study"
        elif articles_score > 0:
            return "articles"
        else:
            # Par défaut, on cherche les articles de loi
            return "articles"

    def _detect_articles(self, query: str) -> List[str]:
        """Detect article references in query"""
        detected_articles = []
        for pattern in ARTICLE_PATTERNS:
            matches = re.findall(pattern, query.lower())
            for match in matches:
                if isinstance(match, tuple):
                    nums = [n for n in match if n.isdigit()]
                    detected_articles.extend(nums)
                else:
                    nums = re.findall(r"\d+", match)
                    detected_articles.extend(nums)
        
        return sorted(list(set(detected_articles)))

    def _enhance_query(self, query: str, detected_articles: List[str]) -> str:
        """Enhance query with article context"""
        if detected_articles:
            enhanced = f"article {' '.join(detected_articles)} {query}"
            logger.info(f"🔢 Requête enrichie avec articles: {detected_articles}")
            return enhanced
        return query

    def enhance_with_article_context(self, results: List[Document]) -> List[Document]:
        """Enhance search results with referenced article context"""
        enhanced_results = []
        for result in results:
            enhanced_results.append(result)
            
            # Pour les documents de type "articles", on peut ajouter les références
            if result.metadata.get("doc_type") == "articles":
                article_refs = result.metadata.get("article_references", [])
                resolved_refs = result.metadata.get("resolved_references", {})
                
                for article_num in article_refs[:3]:
                    if article_num in resolved_refs:
                        ref_doc = Document(
                            page_content=f"Article {article_num} (Référencé): {resolved_refs[article_num][:500]}...",
                            metadata={
                                **result.metadata,
                                "is_reference": True,
                                "referenced_article": article_num,
                                "doc_type": "article_reference"
                            },
                        )
                        enhanced_results.append(ref_doc)
        
        return enhanced_results

    def format_search_results(self, query: str, enhanced_docs: List[Document], 
                            detected_articles: List[str], applied_filters: Dict[str, Any], 
                            country: str, supplemental_message: str = "") -> str:
        """Format search results for system prompt"""
        country_name = "Bénin" if country == "benin" else "Madagascar"
        
        if not enhanced_docs:
            doc_type = applied_filters.get("doc_type", "articles")
            
            if applied_filters.get("fallback_used"):
                # Cas où le fallback a été utilisé mais n'a rien trouvé non plus
                return f"""
**🔍 RECHERCHE JURIDIQUE - {country_name.upper()}**

Aucun document trouvé pour votre requête concernant la jurisprudence.

**💡 Informations :**
- Votre recherche portait sur des décisions de justice
- La base de données sera enrichie avec des décisions de justice prochainement
- En attendant, vous pouvez consulter les articles de loi pour des informations générales

**Filtres appliqués**: {applied_filters}
"""
            else:
                # Cas normal sans fallback
                return f"""
**🔍 RECHERCHE JURIDIQUE - {country_name.upper()}**

Aucun document trouvé avec les critères suivants:
- **Type de document**: {doc_type}
- **Catégorie**: {applied_filters.get('categorie', 'Toutes')}
- **Requête**: "{query}"

**Filtres appliqués**: {applied_filters}
"""

        # Si des documents sont trouvés
        doc_type = applied_filters.get("doc_type", "articles")
        doc_type_fr = "articles de loi" if doc_type == "articles" else "études de cas/jurisprudence"
        
        fallback_note = ""
        if applied_filters.get("fallback_used"):
            fallback_note = f"""
**💡 Note importante :**
Votre requête concernait initialement des **décisions de justice**. 
Comme la base ne contient pas encore de jurisprudence, voici des informations issues des **textes de loi**.
{supplemental_message}
"""
        
        search_results = f"""
**🔍 RECHERCHE JURIDIQUE - {country_name.upper()}**
**Type de documents**: {doc_type_fr}
**Requête**: "{query}"
**Juridiction**: {country_name}
**Articles détectés**: {', '.join(detected_articles) if detected_articles else 'Aucun'}
**Filtres appliqués**: {applied_filters}
**Documents trouvés**: {len(enhanced_docs)}
{fallback_note}
"""

        # Formatage des documents trouvés
        main_docs = [doc for doc in enhanced_docs if not doc.metadata.get("is_reference", False)]
        
        for i, doc in enumerate(main_docs[:5]):
            doc_type = doc.metadata.get("doc_type", "inconnu")
            source = doc.metadata.get('source', 'Non spécifié')
            content = doc.page_content[:600]
            
            search_results += f"""
**📄 DOCUMENT {i+1}** (Type: {doc_type})
- **Source**: {source}
- **Contenu**: {content}...
"""
        
        return search_results