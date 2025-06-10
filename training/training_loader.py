"""
Training data loader for Vanna AI agent.
Automatically loads sample queries and documents from the training_data directory.
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TrainingDataLoader:
    """
    Loads training data from the training_data directory.
    Supports JSON files for sample queries and Markdown files for documents.
    """
    
    def __init__(self, training_data_path: Optional[str] = None):
        """
        Initialize the training data loader.
        
        Args:
            training_data_path (str, optional): Path to training data directory.
                If None, defaults to 'training_data' relative to project root.
        """
        if training_data_path is None:
            # Get project root (one level up from agent directory)
            project_root = Path(__file__).parent.parent
            self.training_data_path = project_root / "training_data"
        else:
            self.training_data_path = Path(training_data_path)
        
        self.sample_queries_path = self.training_data_path / "sample_queries"
        self.documents_path = self.training_data_path / "documents"
    
    def load_sample_queries(self) -> List[Dict]:
        """
        Load all sample queries from JSON files in the sample_queries directory.
        
        Returns:
            List[Dict]: List of query dictionaries with 'question' and 'sql' keys.
        """
        queries = []
        
        if not self.sample_queries_path.exists():
            logger.warning(f"Sample queries directory not found: {self.sample_queries_path}")
            return queries
        
        # Find all JSON files in sample_queries directory
        json_files = list(self.sample_queries_path.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in: {self.sample_queries_path}")
            return queries
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract queries from the file
                file_queries = data.get('queries', [])
                
                # Validate and add queries
                for query in file_queries:
                    if self._validate_query(query):
                        queries.append(query)
                    else:
                        logger.warning(f"Invalid query format in {json_file}: {query}")
                
                # Only log file loading summary, not individual file details
                logger.debug(f"Loaded {len(file_queries)} queries from {json_file.name}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON file {json_file}: {e}")
            except Exception as e:
                logger.error(f"Error loading queries from {json_file}: {e}")
        
        # Final summary only
        if queries:
            logger.info(f"📄 Sample queries loaded: {len(queries)} from {len(json_files)} files")
        return queries
    
    def load_documents(self) -> List[str]:
        """
        Load all documents from Markdown files in the documents directory.
        
        Returns:
            List[str]: List of document contents as strings.
        """
        documents = []
        
        if not self.documents_path.exists():
            logger.warning(f"Documents directory not found: {self.documents_path}")
            return documents
        
        # Find all Markdown files recursively in documents directory
        md_files = list(self.documents_path.rglob("*.md"))
        
        if not md_files:
            logger.warning(f"No Markdown files found in: {self.documents_path}")
            return documents
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if content:
                    documents.append(content)
                    # Only debug log individual documents
                    logger.debug(f"Loaded document: {md_file.relative_to(self.documents_path)}")
                else:
                    logger.warning(f"Empty document: {md_file}")
                
            except Exception as e:
                logger.error(f"Error loading document {md_file}: {e}")
        
        # Final summary only
        if documents:
            logger.info(f"📄 Documents loaded: {len(documents)} from {len(md_files)} files")
        return documents
    
    def _validate_query(self, query: Dict) -> bool:
        """
        Validate that a query dictionary has the required fields.
        
        Args:
            query (Dict): Query dictionary to validate.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        required_fields = ['question', 'sql']
        
        if not isinstance(query, dict):
            return False
        
        for field in required_fields:
            if field not in query or not isinstance(query[field], str) or not query[field].strip():
                return False
        
        return True
    
    def get_training_summary(self) -> Dict:
        """
        Get a summary of available training data.
        
        Returns:
            Dict: Summary with counts and file information.
        """
        summary = {
            'sample_queries': {
                'total_files': 0,
                'total_queries': 0,
                'files': []
            },
            'documents': {
                'total_files': 0,
                'files': []
            }
        }
        
        # Count sample query files
        if self.sample_queries_path.exists():
            json_files = list(self.sample_queries_path.glob("*.json"))
            summary['sample_queries']['total_files'] = len(json_files)
            summary['sample_queries']['files'] = [f.name for f in json_files]
            
            # Count total queries
            queries = self.load_sample_queries()
            summary['sample_queries']['total_queries'] = len(queries)
        
        # Count document files
        if self.documents_path.exists():
            md_files = list(self.documents_path.rglob("*.md"))
            summary['documents']['total_files'] = len(md_files)
            summary['documents']['files'] = [str(f.relative_to(self.documents_path)) for f in md_files]
        
        return summary 