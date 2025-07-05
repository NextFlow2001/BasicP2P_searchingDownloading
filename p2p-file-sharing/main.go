package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/ipfs/go-cid"
	"github.com/libp2p/go-libp2p"
	dht "github.com/libp2p/go-libp2p-kad-dht"
	"github.com/libp2p/go-libp2p/core/host"
	"github.com/libp2p/go-libp2p/core/network"
	"github.com/libp2p/go-libp2p/core/peer"
	ma "github.com/multiformats/go-multiaddr"
	mh "github.com/multiformats/go-multihash"
)

// P2PNode representa un nodo en la red P2P
type P2PNode struct {
	Host            host.Host
	DHT             *dht.IpfsDHT
	FragmentMgr     *FragmentManager
	StoredFragments map[string]Fragment
	FileMetadata    map[string]FileInfo
}

// FileInfo contiene metadatos del archivo
type FileInfo struct {
	Filename       string
	FragmentHashes []string
	TotalFragments int
}

// FragmentRequest representa una solicitud de fragmento
type FragmentRequest struct {
	Hash string `json:"hash"`
}

// FragmentResponse representa la respuesta de un fragmento
type FragmentResponse struct {
	Hash  string `json:"hash"`
	Data  []byte `json:"data"`
	Found bool   `json:"found"`
}

// NewP2PNode crea un nuevo nodo P2P
func NewP2PNode(port int, bootstrapAddrs []string) (*P2PNode, error) {
	ctx := context.Background()

	// Crear nodo libp2p
	listenAddr, _ := ma.NewMultiaddr(fmt.Sprintf("/ip4/0.0.0.0/tcp/%d", port))
	node, err := libp2p.New(
		libp2p.ListenAddrs(listenAddr),
	)
	if err != nil {
		return nil, err
	}

	// Iniciar DHT en modo completo
	kademliaDHT, err := dht.New(ctx, node, dht.Mode(dht.ModeServer))
	if err != nil {
		node.Close()
		return nil, err
	}

	// Bootstrap DHT
	if err = kademliaDHT.Bootstrap(ctx); err != nil {
		node.Close()
		return nil, err
	}

	// Conectar a nodos bootstrap
	for _, addr := range bootstrapAddrs {
		maddr, err := ma.NewMultiaddr(addr)
		if err != nil {
			log.Printf("Error analizando dirección bootstrap: %v", err)
			continue
		}
		peerInfo, err := peer.AddrInfoFromP2pAddr(maddr)
		if err != nil {
			log.Printf("Error creando información de peer: %v", err)
			continue
		}
		err = node.Connect(ctx, *peerInfo)
		if err != nil {
			log.Printf("Error conectando a bootstrap: %v", err)
		}
	}

	// Crear nodo
	p2pNode := &P2PNode{
		Host:            node,
		DHT:             kademliaDHT,
		FragmentMgr:     NewFragmentManager(256 * 1024), // 256KB por fragmento
		StoredFragments: make(map[string]Fragment),
		FileMetadata:    make(map[string]FileInfo),
	}

	// Configurar handler para fragmentos
	node.SetStreamHandler("/fragment/1.0.0", p2pNode.handleFragmentRequest)

	return p2pNode, nil
}

// handleFragmentRequest maneja solicitudes de fragmentos
func (n *P2PNode) handleFragmentRequest(s network.Stream) {
	defer s.Close()

	// Leer la solicitud
	decoder := json.NewDecoder(s)
	var req FragmentRequest
	if err := decoder.Decode(&req); err != nil {
		log.Printf("Error decodificando solicitud: %v", err)
		return
	}

	// Buscar el fragmento
	response := FragmentResponse{
		Hash:  req.Hash,
		Found: false,
	}

	if fragment, exists := n.StoredFragments[req.Hash]; exists {
		response.Data = fragment.Data
		response.Found = true
	}

	// Enviar respuesta
	encoder := json.NewEncoder(s)
	if err := encoder.Encode(response); err != nil {
		log.Printf("Error enviando respuesta: %v", err)
	}
}

// UploadFile sube un archivo a la red
func (n *P2PNode) UploadFile(filepath string) error {
	ctx := context.Background()
	fragments, err := n.FragmentMgr.FragmentFile(filepath)
	if err != nil {
		return err
	}

	filename := filepath
	fragmentHashes := make([]string, len(fragments))

	// Almacenar fragmentos localmente
	for i, fragment := range fragments {
		fragmentHashes[i] = fragment.Hash
		n.StoredFragments[fragment.Hash] = fragment
	}

	// Almacenar metadatos del archivo localmente y en la DHT
	fileInfo := FileInfo{
		Filename:       filename,
		FragmentHashes: fragmentHashes,
		TotalFragments: len(fragments),
	}
	n.FileMetadata[filename] = fileInfo

	fileInfoBytes, err := json.Marshal(fileInfo)
	if err != nil {
		return fmt.Errorf("error codificando metadatos del archivo: %v", err)
	}
	// Crear CID para el archivo
	hash, err := mh.Sum([]byte(filename), mh.SHA2_256, -1)
	if err != nil {
		return fmt.Errorf("error generando hash para archivo %s: %v", filename, err)
	}
	fileCid := cid.NewCidV1(cid.Raw, hash)
	err = n.DHT.PutValue(ctx, fileCid.String(), fileInfoBytes)
	if err != nil {
		return fmt.Errorf("error almacenando metadatos del archivo: %v", err)
	}

	log.Printf("Archivo %s subido con %d fragmentos", filename, len(fragments))
	return nil
}

func main() {
	if len(os.Args) < 4 {
		log.Fatal("Uso: go run main.go fragment.go <puerto> upload <archivo> [bootstrap]")
	}

	portStr := os.Args[1]
	command := os.Args[2]
	filename := os.Args[3]
	bootstrapAddrs := []string{}
	if len(os.Args) > 4 {
		bootstrapAddrs = strings.Split(os.Args[4], ",")
	}

	// Convertir puerto a entero
	port, err := strconv.Atoi(portStr)
	if err != nil {
		log.Fatalf("Puerto inválido: %v", err)
	}

	// Crear nodo
	node, err := NewP2PNode(port, bootstrapAddrs)
	if err != nil {
		log.Fatalf("Error creando nodo: %v", err)
	}
	defer node.Host.Close()

	log.Printf("Nodo P2P iniciado en puerto %d", port)
	log.Printf("ID del nodo: %s", node.Host.ID().String())

	// Dar tiempo para que el DHT se inicialice
	time.Sleep(2 * time.Second)

	// Ejecutar comando
	if command == "upload" {
		err = node.UploadFile(filename)
		if err != nil {
			log.Fatalf("Error subiendo archivo: %v", err)
		}
		log.Println("Archivo subido exitosamente")

		// Mantener el nodo corriendo para servir el archivo
		log.Println("Manteniendo nodo activo para servir archivos...")
		select {}
	} else {
		log.Fatal("Comando desconocido: use 'upload'")
	}
}