import asyncio
import hashlib
import json
import os
import time
from typing import Dict, List, Optional, Tuple
from kademlia.network import Server
import aiofiles
from dataclasses import dataclass
import struct
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Fragment:
    """Representa un fragmento de archivo"""
    hash: str
    size: int
    index: int
    total_fragments: int
    filename: str
    data: bytes = None

class FragmentManager:
    """Gestor de fragmentación y ensamblaje de archivos"""
    
    def __init__(self, fragment_size: int = 256 * 1024):  # 256KB por defecto
        self.fragment_size = fragment_size
        self.fragments_cache: Dict[str, Fragment] = {}
    
    def fragment_file(self, filepath: str) -> List[Fragment]:
        """Divide un archivo en fragmentos"""
        fragments = []
        filename = os.path.basename(filepath)
        
        with open(filepath, 'rb') as file:
            file_data = file.read()
            file_size = len(file_data)
            total_fragments = (file_size + self.fragment_size - 1) // self.fragment_size
            
            for i in range(total_fragments):
                start = i * self.fragment_size
                end = min(start + self.fragment_size, file_size)
                fragment_data = file_data[start:end]
                
                # Calcular hash del fragmento
                fragment_hash = hashlib.sha256(fragment_data).hexdigest()
                
                fragment = Fragment(
                    hash=fragment_hash,
                    size=len(fragment_data),
                    index=i,
                    total_fragments=total_fragments,
                    filename=filename,
                    data=fragment_data
                )
                
                fragments.append(fragment)
                self.fragments_cache[fragment_hash] = fragment
        
        logger.info(f"Archivo {filename} fragmentado en {total_fragments} partes")
        return fragments
    
    def assemble_file(self, fragments: List[Fragment], output_path: str) -> bool:
        """Ensambla fragmentos en un archivo completo"""
        if not fragments:
            return False
        
        # Ordenar fragmentos por índice
        fragments.sort(key=lambda x: x.index)
        
        # Verificar que tenemos todos los fragmentos
        expected_fragments = fragments[0].total_fragments
        if len(fragments) != expected_fragments:
            logger.error(f"Faltan fragmentos: {len(fragments)}/{expected_fragments}")
            return False
        
        try:
            with open(output_path, 'wb') as output_file:
                for fragment in fragments:
                    if fragment.data:
                        output_file.write(fragment.data)
                    else:
                        logger.error(f"Fragmento {fragment.index} sin datos")
                        return False
            
            logger.info(f"Archivo ensamblado exitosamente en {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error ensamblando archivo: {e}")
            return False
    
    def get_fragment_info(self, fragment_hash: str) -> Optional[Fragment]:
        """Obtiene información de un fragmento por su hash"""
        return self.fragments_cache.get(fragment_hash)

class P2PNode:
    """Nodo P2P principal"""
    
    def __init__(self, node_id: str, port: int):
        self.node_id = node_id
        self.port = port
        self.server = Server()
        self.fragment_manager = FragmentManager()
        self.active_downloads: Dict[str, Dict] = {}
        self.stored_fragments: Dict[str, Fragment] = {}
        self.file_registry: Dict[str, List[str]] = {}  # filename -> [fragment_hashes]
        self.running = False
    
    async def start(self, bootstrap_nodes: List[Tuple[str, int]] = None):
        """Inicia el nodo P2P"""
        try:
            await self.server.listen(self.port)
            logger.info(f"Nodo {self.node_id} escuchando en puerto {self.port}")
            
            if bootstrap_nodes:
                await self.server.bootstrap(bootstrap_nodes)
                logger.info(f"Conectado a nodos bootstrap: {bootstrap_nodes}")
            
            self.running = True
            logger.info(f"Nodo {self.node_id} iniciado exitosamente")
            
        except Exception as e:
            logger.error(f"Error iniciando nodo: {e}")
            raise
    
    async def stop(self):
        """Detiene el nodo P2P"""
        self.running = False
        self.server.stop()
        logger.info(f"Nodo {self.node_id} detenido")
    
    async def store_file(self, filepath: str) -> bool:
        """Almacena un archivo fragmentándolo en la red"""
        try:
            # Fragmentar archivo
            fragments = self.fragment_manager.fragment_file(filepath)
            filename = os.path.basename(filepath)
            
            # Almacenar fragmentos localmente
            fragment_hashes = []
            for fragment in fragments:
                self.stored_fragments[fragment.hash] = fragment
                fragment_hashes.append(fragment.hash)
                
                # Registrar fragmento en DHT
                fragment_info = {
                    'node_id': self.node_id,
                    'node_address': ('127.0.0.1', self.port),
                    'filename': filename,
                    'index': fragment.index,
                    'total_fragments': fragment.total_fragments,
                    'size': fragment.size
                }
                
                await self.server.set(fragment.hash, json.dumps(fragment_info))
                logger.info(f"Fragmento {fragment.index} registrado: {fragment.hash[:8]}...")
            
            # Registrar archivo completo
            self.file_registry[filename] = fragment_hashes
            file_info = {
                'filename': filename,
                'fragment_hashes': fragment_hashes,
                'total_fragments': len(fragments),
                'file_size': sum(f.size for f in fragments),
                'node_id': self.node_id
            }
            
            await self.server.set(f"file:{filename}", json.dumps(file_info))
            logger.info(f"Archivo {filename} almacenado con {len(fragments)} fragmentos")
            return True
            
        except Exception as e:
            logger.error(f"Error almacenando archivo {filepath}: {e}")
            return False
    
    async def search_file(self, filename: str) -> Optional[Dict]:
        """Busca un archivo en la red P2P"""
        try:
            file_info_str = await self.server.get(f"file:{filename}")
            if file_info_str:
                file_info = json.loads(file_info_str)
                logger.info(f"Archivo encontrado: {filename}")
                return file_info
            else:
                logger.info(f"Archivo no encontrado: {filename}")
                return None
        except Exception as e:
            logger.error(f"Error buscando archivo {filename}: {e}")
            return None
    
    async def download_fragment(self, fragment_hash: str, peer_address: Tuple[str, int]) -> Optional[Fragment]:
        """Descarga un fragmento específico de un peer"""
        try:
            # En una implementación real, esto sería una conexión directa TCP/UDP
            # Por simplicidad, simulamos que obtenemos el fragmento del nodo local
            if fragment_hash in self.stored_fragments:
                fragment = self.stored_fragments[fragment_hash]
                logger.info(f"Fragmento descargado localmente: {fragment_hash[:8]}...")
                return fragment
            else:
                # Simular descarga desde peer remoto
                await asyncio.sleep(0.1)  # Simular latencia de red
                logger.warning(f"Fragmento no disponible: {fragment_hash[:8]}...")
                return None
                
        except Exception as e:
            logger.error(f"Error descargando fragmento {fragment_hash}: {e}")
            return None
    
    async def download_file(self, filename: str, output_path: str) -> bool:
        """Descarga un archivo completo de la red P2P"""
        try:
            # Buscar información del archivo
            file_info = await self.search_file(filename)
            if not file_info:
                logger.error(f"Archivo no encontrado: {filename}")
                return False
            
            fragment_hashes = file_info['fragment_hashes']
            total_fragments = file_info['total_fragments']
            
            logger.info(f"Iniciando descarga de {filename} ({total_fragments} fragmentos)")
            
            # Obtener información de cada fragmento
            download_tasks = []
            fragment_peers = {}
            
            for fragment_hash in fragment_hashes:
                fragment_info_str = await self.server.get(fragment_hash)
                if fragment_info_str:
                    fragment_info = json.loads(fragment_info_str)
                    peer_address = tuple(fragment_info['node_address'])
                    fragment_peers[fragment_hash] = peer_address
                    
                    # Crear tarea de descarga
                    task = self.download_fragment(fragment_hash, peer_address)
                    download_tasks.append(task)
                else:
                    logger.error(f"No se pudo obtener info del fragmento: {fragment_hash[:8]}...")
                    return False
            
            # Ejecutar descargas en paralelo
            start_time = time.time()
            fragments = await asyncio.gather(*download_tasks, return_exceptions=True)
            download_time = time.time() - start_time
            
            # Filtrar fragmentos válidos
            valid_fragments = [f for f in fragments if isinstance(f, Fragment)]
            
            if len(valid_fragments) != total_fragments:
                logger.error(f"Descarga incompleta: {len(valid_fragments)}/{total_fragments}")
                return False
            
            # Ensamblar archivo
            success = self.fragment_manager.assemble_file(valid_fragments, output_path)
            if success:
                total_size = sum(f.size for f in valid_fragments)
                speed = total_size / download_time / 1024 / 1024  # MB/s
                logger.info(f"Descarga completada: {filename}")
                logger.info(f"Tiempo: {download_time:.2f}s, Velocidad: {speed:.2f} MB/s")
            
            return success
            
        except Exception as e:
            logger.error(f"Error descargando archivo {filename}: {e}")
            return False
    
    async def list_stored_files(self) -> List[str]:
        """Lista archivos almacenados en este nodo"""
        return list(self.file_registry.keys())
    
    async def get_network_stats(self) -> Dict:
        """Obtiene estadísticas de la red"""
        try:
            # En Kademlia, no hay una forma directa de contar nodos
            # Esto es una aproximación
            routing_table_size = len(self.server.protocol.router.buckets)
            
            stats = {
                'node_id': self.node_id,
                'port': self.port,
                'stored_fragments': len(self.stored_fragments),
                'stored_files': len(self.file_registry),
                'routing_table_size': routing_table_size,
                'active_downloads': len(self.active_downloads),
                'running': self.running
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}

class P2PNetwork:
    """Gestor de red P2P con múltiples nodos"""
    
    def __init__(self):
        self.nodes: Dict[str, P2PNode] = {}
        self.bootstrap_port = 8468
    
    async def create_bootstrap_node(self) -> P2PNode:
        """Crea el nodo bootstrap inicial"""
        bootstrap_node = P2PNode("bootstrap", self.bootstrap_port)
        await bootstrap_node.start()
        self.nodes["bootstrap"] = bootstrap_node
        logger.info("Nodo bootstrap creado")
        return bootstrap_node
    
    async def add_node(self, node_id: str, port: int) -> P2PNode:
        """Agrega un nuevo nodo a la red"""
        node = P2PNode(node_id, port)
        bootstrap_nodes = [("127.0.0.1", self.bootstrap_port)]
        await node.start(bootstrap_nodes)
        self.nodes[node_id] = node
        logger.info(f"Nodo {node_id} agregado a la red")
        return node
    
    async def shutdown_network(self):
        """Apaga toda la red P2P"""
        for node in self.nodes.values():
            await node.stop()
        self.nodes.clear()
        logger.info("Red P2P apagada")

# Ejemplo de uso y pruebas
async def demo_p2p_system():
    """Demostración del sistema P2P"""
    print("=== Demo Sistema P2P ===")
    
    # Crear red P2P
    network = P2PNetwork()
    
    try:
        # Crear nodo bootstrap
        await network.create_bootstrap_node()
        await asyncio.sleep(1)
        
        # Agregar nodos adicionales
        node1 = await network.add_node("node1", 8469)
        node2 = await network.add_node("node2", 8470)
        await asyncio.sleep(2)
        
        # Crear archivo de prueba
        test_file = "test_file.txt"
        with open(test_file, 'w') as f:
            f.write("Este es un archivo de prueba para el sistema P2P.\n" * 100)
        
        print(f"Archivo de prueba creado: {test_file}")
        
        # Almacenar archivo en node1
        print("Almacenando archivo en node1...")
        success = await node1.store_file(test_file)
        if success:
            print("✓ Archivo almacenado exitosamente")
        else:
            print("✗ Error almacenando archivo")
            return
        
        await asyncio.sleep(2)
        
        # Buscar archivo desde node2
        print("Buscando archivo desde node2...")
        file_info = await node2.search_file(os.path.basename(test_file))
        if file_info:
            print(f"✓ Archivo encontrado: {file_info['filename']}")
            print(f"  Fragmentos: {file_info['total_fragments']}")
            print(f"  Tamaño: {file_info['file_size']} bytes")
        else:
            print("✗ Archivo no encontrado")
            return
        
        # Descargar archivo en node2
        print("Descargando archivo en node2...")
        output_file = "downloaded_" + test_file
        success = await node2.download_file(os.path.basename(test_file), output_file)
        if success:
            print(f"✓ Archivo descargado como: {output_file}")
            
            # Verificar integridad
            with open(test_file, 'rb') as f1, open(output_file, 'rb') as f2:
                if f1.read() == f2.read():
                    print("✓ Integridad verificada: archivos idénticos")
                else:
                    print("✗ Error de integridad: archivos diferentes")
        else:
            print("✗ Error descargando archivo")
        
        # Mostrar estadísticas
        print("\n=== Estadísticas de Red ===")
        for node_id, node in network.nodes.items():
            stats = await node.get_network_stats()
            print(f"Nodo {node_id}:")
            print(f"  Fragmentos almacenados: {stats.get('stored_fragments', 0)}")
            print(f"  Archivos almacenados: {stats.get('stored_files', 0)}")
            print(f"  Estado: {'Activo' if stats.get('running', False) else 'Inactivo'}")
        
        await asyncio.sleep(1)
        
    finally:
        # Limpiar
        await network.shutdown_network()
        
        # Eliminar archivos de prueba
        for file in [test_file, "downloaded_" + test_file]:
            if os.path.exists(file):
                os.remove(file)
        
        print("\n=== Demo completada ===")

if __name__ == "__main__":
    # Ejecutar demo
    asyncio.run(demo_p2p_system())