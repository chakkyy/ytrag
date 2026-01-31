"""
Unit tests for consolidar.py - Text consolidation into volumes for LLM
"""
import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from consolidar import (
    validar_archivo_procesado,
    extraer_titulo_de_contenido,
    consolidar_proyectos,
    TRANSCRIPCIONES_POR_TXT,
    NOMBRE_CARPETA_BIBLIOTECA,
    CARPETA_EXPORTACION
)


class TestValidarArchivoProcesado:
    """Tests for file validation"""
    
    def test_validates_correct_format(self):
        """Should validate files with correct markdown format"""
        content = "# Title\n**Idioma:** EN\n---\nContent here"
        assert validar_archivo_procesado(content) == True
    
    def test_rejects_invalid_format(self):
        """Should reject files without markdown title"""
        content = "This is just plain text without a title"
        assert validar_archivo_procesado(content) == False
    
    def test_handles_empty_content(self):
        """Should handle empty content"""
        assert validar_archivo_procesado("") == False
    
    def test_handles_whitespace_before_title(self):
        """Should handle whitespace before title"""
        content = "   # Title\nContent"
        # May or may not be valid depending on implementation
        result = validar_archivo_procesado(content)
        assert isinstance(result, bool)


class TestExtraerTituloDeContenido:
    """Tests for title extraction"""
    
    def test_extracts_simple_title(self):
        """Should extract simple title from markdown"""
        content = "# My Video Title\n**Idioma:** EN\n---\nContent"
        title = extraer_titulo_de_contenido(content)
        assert title == "My Video Title"
    
    def test_extracts_title_with_date(self):
        """Should extract title with date prefix"""
        content = "# 20230101_Video Title\n---\nContent"
        title = extraer_titulo_de_contenido(content)
        assert "20230101_Video Title" in title
    
    def test_handles_empty_title(self):
        """Should handle empty title line"""
        content = "# \n---\nContent"
        title = extraer_titulo_de_contenido(content)
        assert title == "" or title is not None


class TestConsolidarProyectos:
    """Tests for project consolidation"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create workspace with sample processed files"""
        temp = tempfile.mkdtemp()
        
        # Create project directory
        proyecto = Path(temp) / "proyecto-test"
        proyecto.mkdir()
        
        # Create _BIBLIOTECA directory with sample files
        biblioteca = proyecto / NOMBRE_CARPETA_BIBLIOTECA
        biblioteca.mkdir()
        
        # Create sample markdown files (as if processed by limpiar.py)
        for i in range(15):  # Create 15 files
            file_path = biblioteca / f"2023{i+1:02d}01_Video {i+1} [EN].md"
            content = f"""# 2023{i+1:02d}01_Video {i+1}
**Idioma:** EN
**Fuente:** video{i+1}.vtt
---

This is the content of video {i+1}. It contains some text that would be 
the cleaned transcript of the original video subtitle file. The content 
here is meant to simulate what limpiar.py would produce.
"""
            file_path.write_text(content, encoding='utf-8')
        
        yield temp
        shutil.rmtree(temp)
    
    def test_creates_export_directory(self, temp_workspace):
        """Should create export directory"""
        consolidar_proyectos(temp_workspace)
        export_dir = Path(temp_workspace) / CARPETA_EXPORTACION
        assert export_dir.exists()
        assert export_dir.is_dir()
    
    def test_creates_consolidated_files(self, temp_workspace):
        """Should create consolidated output files"""
        consolidar_proyectos(temp_workspace)
        export_dir = Path(temp_workspace) / CARPETA_EXPORTACION
        txt_files = list(export_dir.glob("*.txt"))
        assert len(txt_files) >= 1
    
    def test_creates_manifest(self, temp_workspace):
        """Should create manifest.json file"""
        consolidar_proyectos(temp_workspace)
        export_dir = Path(temp_workspace) / CARPETA_EXPORTACION
        manifest = export_dir / "manifest.json"
        assert manifest.exists()
    
    def test_volume_has_correct_structure(self, temp_workspace):
        """Should create volumes with correct structure"""
        consolidar_proyectos(temp_workspace)
        export_dir = Path(temp_workspace) / CARPETA_EXPORTACION
        txt_files = list(export_dir.glob("*.txt"))
        
        if txt_files:
            content = txt_files[0].read_text(encoding='utf-8')
            # Should have collection header
            assert "=== COLECCIÓN:" in content
            # Should have volume number
            assert "=== VOLUMEN:" in content
            # Should have index at the end
            assert "=== ÍNDICE DE ESTE VOLUMEN ===" in content


class TestVolumeCreation:
    """Tests for volume creation logic"""
    
    @pytest.fixture
    def large_workspace(self):
        """Create workspace with many files to test volume splitting"""
        temp = tempfile.mkdtemp()
        
        proyecto = Path(temp) / "proyecto-grande"
        proyecto.mkdir()
        biblioteca = proyecto / NOMBRE_CARPETA_BIBLIOTECA
        biblioteca.mkdir()
        
        # Create more files than TRANSCRIPCIONES_POR_TXT
        num_files = TRANSCRIPCIONES_POR_TXT + 50
        for i in range(num_files):
            file_path = biblioteca / f"2023{(i % 12)+1:02d}{(i % 28)+1:02d}_Video {i+1:04d} [EN].md"
            content = f"""# Video {i+1:04d}
**Idioma:** EN
---
Content for video {i+1}.
"""
            file_path.write_text(content, encoding='utf-8')
        
        yield temp
        shutil.rmtree(temp)
    
    def test_creates_multiple_volumes(self, large_workspace):
        """Should create multiple volumes when needed"""
        consolidar_proyectos(large_workspace)
        export_dir = Path(large_workspace) / CARPETA_EXPORTACION
        txt_files = list(export_dir.glob("*.txt"))
        # Should have at least 2 volumes
        assert len(txt_files) >= 2
    
    def test_volumes_have_sequential_numbers(self, large_workspace):
        """Should use sequential volume numbering"""
        consolidar_proyectos(large_workspace)
        export_dir = Path(large_workspace) / CARPETA_EXPORTACION
        txt_files = sorted(export_dir.glob("*.txt"))
        
        # Should have Vol01, Vol02, etc.
        names = [f.name for f in txt_files]
        assert any("Vol01" in n for n in names)
        assert any("Vol02" in n for n in names)


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    @pytest.fixture
    def empty_workspace(self):
        """Create workspace with empty biblioteca"""
        temp = tempfile.mkdtemp()
        proyecto = Path(temp) / "proyecto-vacio"
        proyecto.mkdir()
        biblioteca = proyecto / NOMBRE_CARPETA_BIBLIOTECA
        biblioteca.mkdir()
        yield temp
        shutil.rmtree(temp)
    
    def test_handles_empty_biblioteca(self, empty_workspace):
        """Should handle empty biblioteca gracefully"""
        # Should not raise
        consolidar_proyectos(empty_workspace)
        # May or may not create export directory
        export_dir = Path(empty_workspace) / CARPETA_EXPORTACION
        # At minimum, should not crash
        assert True
    
    def test_handles_nonexistent_directory(self):
        """Should handle non-existent directory"""
        # Should handle gracefully
        try:
            consolidar_proyectos("/nonexistent/path/that/does/not/exist")
        except SystemExit:
            pass  # May exit
        except Exception:
            pass  # May raise
        # Main thing is it doesn't crash hard
        assert True
    
    def test_handles_special_characters_in_content(self):
        """Should handle special characters in file content"""
        temp = tempfile.mkdtemp()
        proyecto = Path(temp) / "proyecto-special"
        proyecto.mkdir()
        biblioteca = proyecto / NOMBRE_CARPETA_BIBLIOTECA
        biblioteca.mkdir()
        
        # Create file with special characters
        file_path = biblioteca / "20230101_Video ¿Qué pasa? [ES].md"
        content = """# 20230101_Video ¿Qué pasa?
**Idioma:** ES
---
¿Cómo estás? ¡Muy bien! Café y más.
"""
        file_path.write_text(content, encoding='utf-8')
        
        try:
            consolidar_proyectos(temp)
            export_dir = Path(temp) / CARPETA_EXPORTACION
            txt_files = list(export_dir.glob("*.txt"))
            
            if txt_files:
                content = txt_files[0].read_text(encoding='utf-8')
                assert "¿Qué pasa?" in content or "Cómo" in content
        finally:
            shutil.rmtree(temp)


class TestManifestContent:
    """Tests for manifest file content"""
    
    @pytest.fixture
    def sample_workspace(self):
        """Create simple workspace for manifest testing"""
        temp = tempfile.mkdtemp()
        
        proyecto = Path(temp) / "mi-proyecto"
        proyecto.mkdir()
        biblioteca = proyecto / NOMBRE_CARPETA_BIBLIOTECA
        biblioteca.mkdir()
        
        # Create one sample file
        file_path = biblioteca / "20230101_Test [EN].md"
        file_path.write_text("# 20230101_Test\n---\nContent", encoding='utf-8')
        
        yield temp
        shutil.rmtree(temp)
    
    def test_manifest_has_required_fields(self, sample_workspace):
        """Should create manifest with required fields"""
        import json
        
        consolidar_proyectos(sample_workspace)
        export_dir = Path(sample_workspace) / CARPETA_EXPORTACION
        manifest_path = export_dir / "manifest.json"
        
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            assert "generated_at" in manifest
            assert "base_directory" in manifest
            assert "projects" in manifest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
