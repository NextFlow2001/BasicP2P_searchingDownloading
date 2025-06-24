# 🌐 Sistema P2P Básico para Búsqueda y Descarga de Archivos

¡Bienvenido a este proyecto! 🚀 Este repositorio contiene un **sistema P2P básico** implementado en **Python** que utiliza una tabla de hash distribuida (DHT) basada en el protocolo **Kademlia** para fragmentar, distribuir, buscar y descargar archivos en una red descentralizada. Verifica la integridad de los datos con hashes SHA-256 y soporta transferencias paralelas. 🗂️

## 📋 Requisitos

- **Python**: Versión 3.9 o superior 🐍
- **Dependencias**:
  - `kademlia`: Para la DHT y la red P2P 🔗
  - `aiofiles`: Operaciones de archivo asíncronas 📁
  - `cryptography`: Hashes SHA-256 para integridad 🔒

## 🛠️ Instalación

1. **Clona el repositorio**:
   ```bash
   git clone https://github.com/NextFlow2001/BasicP2P_searchingDownloading.git
   cd BasicP2P_searchingDownloading
   ```

2. **Crea un entorno virtual** (¡recomendado!):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   .\venv\Scripts\activate   # Windows
   ```

3. **Instala las dependencias**:
   ```bash
   pip install kademlia aiofiles cryptography
   ```

## 📂 Estructura del Proyecto

- `p2p_system.py`: Script principal con las clases:
  - `FragmentManager`: Gestiona fragmentación y ensamblaje de archivos 📄
  - `P2PNode`: Maneja nodos P2P y transferencias 🔌
  - `P2PNetwork`: Coordina la red P2P 🌐

## 🚀 Cómo Ejecutar

1. **Verifica los puertos**:
   - El sistema usa los puertos **8468, 8469, 8470** (Kademlia) y **9468, 9469, 9470** (TCP). Asegúrate de que estén libres:
     ```bash
     netstat -an | grep 8468  # Linux/macOS
     netstat -an | findstr 8468  # Windows
     ```
   - Si están ocupados, edita `p2p_system.py` (cambia `bootstrap_port = 8468` y `port + 1000` en `P2PNode`).

2. **Ejecuta la demo**:
   - Desde la terminal, en el directorio del proyecto:
     ```bash
     python p2p_system.py
     ```
   - La demo:
     - Crea una red P2P con 3 nodos (bootstrap, node1, node2) 🌍
     - Genera un archivo de prueba (`test_file.txt`) 📝
     - Lo fragmenta y almacena en `node1` 💾
     - Lo busca y descarga desde `node2` 📥
     - Verifica la integridad del archivo descargado ✅
     - Muestra estadísticas y limpia los archivos 🧹

3. **Salida esperada**:
   ```
   === Demo Sistema P2P ===
   Archivo de prueba creado: test_file.txt
   Almacenando archivo en node1...
   ✓ Archivo almacenado exitosamente
   Buscando archivo desde node2...
   ✓ Archivo encontrado: test_file.txt
     Fragmentos: 1
     Tamaño: 5100 bytes
   Descargando archivo en node2...
   ✓ Archivo descargado como: downloaded_test_file.txt
   ✓ Integridad verificada: archivos idénticos
   === Estadísticas de Red ===
   Nodo bootstrap:
     Fragmentos almacenados: 0
     Archivos almacenados: 0
     Estado: Activo
   Nodo node1:
     Fragmentos almacenados: 1
     Archivos almacenados: 1
     Estado: Activo
   Nodo node2:
     Fragmentos almacenados: 0
     Archivos almacenados: 0
     Estado: Activo
   === Demo completada ===
   ```

## ⚠️ Notas y Solución de Problemas

- **Entorno de prueba**: La demo usa `localhost` (127.0.0.1). Para redes reales, ajusta las IPs en `P2PNode` y `P2PNetwork`.
- **Errores comunes**:
  - **"Address already in use"**: Cambia los puertos en `p2p_system.py` (por ejemplo, `bootstrap_port = 8480`, `port + 2000`).
  - **"ModuleNotFoundError"**: Verifica las dependencias con `pip list` y asegúrate de estar en el entorno virtual correcto.
  - **Fallo en descarga**: Revisa los logs (`INFO`, `ERROR`) para depurar problemas de conexión TCP o DHT.
- **Limitaciones**:
  - Usa TCP simple para transferencias, no óptimo para redes grandes 📡
  - No soporta tolerancia a churn ni seguridad avanzada 🛡️
  - La demo usa un archivo pequeño (5 KB). Para archivos grandes, modifica `demo_p2p_system` 📈

## 📜 Licencia
¡Úsalo y compártelo libremente! 🎉
