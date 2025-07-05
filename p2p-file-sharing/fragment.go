//fragment.go

package main

import (
    "crypto/sha256"
    "fmt"
    "io"
    "os"
    "sort"
)

// Fragment representa un fragmento de archivo
type Fragment struct {
    Hash          string
    Data          []byte
    Index         int
    TotalFragments int
    Filename      string
}

// FragmentManager gestiona la fragmentación y ensamblaje
type FragmentManager struct {
    FragmentSize int
}

// NewFragmentManager crea un nuevo gestor de fragmentos
func NewFragmentManager(fragmentSize int) *FragmentManager {
    return &FragmentManager{FragmentSize: fragmentSize}
}

// FragmentFile divide un archivo en fragmentos
func (fm *FragmentManager) FragmentFile(filepath string) ([]Fragment, error) {
    file, err := os.Open(filepath)
    if err != nil {
        return nil, fmt.Errorf("error leyendo archivo: %v", err)
    }
    defer file.Close()

    data, err := io.ReadAll(file)
    if err != nil {
        return nil, fmt.Errorf("error leyendo datos: %v", err)
    }

    filename := filepath
    totalFragments := (len(data) + fm.FragmentSize - 1) / fm.FragmentSize
    fragments := make([]Fragment, 0, totalFragments)

    for i := 0; i < totalFragments; i++ {
        start := i * fm.FragmentSize
        end := start + fm.FragmentSize
        if end > len(data) {
            end = len(data)
        }
        fragmentData := data[start:end]
        hash := fmt.Sprintf("%x", sha256.Sum256(fragmentData))

        fragment := Fragment{
            Hash:          hash,
            Data:          fragmentData,
            Index:         i,
            TotalFragments: totalFragments,
            Filename:      filename,
        }
        fragments = append(fragments, fragment)
    }
    return fragments, nil
}

// AssembleFile ensambla fragmentos en un archivo
func (fm *FragmentManager) AssembleFile(fragments []Fragment, outputPath string) error {
    if len(fragments) == 0 {
        return fmt.Errorf("no hay fragmentos para ensamblar")
    }

    // Ordenar fragmentos por índice
    sort.Slice(fragments, func(i, j int) bool {
        return fragments[i].Index < fragments[j].Index
    })

    // Verificar que tenemos todos los fragmentos
    if len(fragments) != fragments[0].TotalFragments {
        return fmt.Errorf("fragmentos incompletos: %d/%d", len(fragments), fragments[0].TotalFragments)
    }

    // Ensamblar
    outputFile, err := os.Create(outputPath)
    if err != nil {
        return fmt.Errorf("error creando archivo: %v", err)
    }
    defer outputFile.Close()

    for _, fragment := range fragments {
        if _, err := outputFile.Write(fragment.Data); err != nil {
            return fmt.Errorf("error escribiendo fragmento: %v", err)
        }
    }
    return nil
}