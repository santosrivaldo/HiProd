import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import api from "../services/api";
import { PrinterIcon, ArrowDownTrayIcon, ArrowUpTrayIcon } from "@heroicons/react/24/outline";
import { exportToCSV, printData } from "../utils/exportUtils";
import { canEditTags } from "../utils/permissions";

const TagManagement = () => {
  const { user } = useAuth();
  const allowEditTags = canEditTags(user?.perfil);
  const [tags, setTags] = useState([]);
  const [filteredTags, setFilteredTags] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingTag, setEditingTag] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState("");
  const [importLoading, setImportLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategoria, setFilterCategoria] = useState("");
  const [filterProdutividade, setFilterProdutividade] = useState("");
  const [filterAtivo, setFilterAtivo] = useState("");
  const fileInputRef = React.useRef(null);
  const [formData, setFormData] = useState({
    nome: "",
    descricao: "",
    cor: "#6B7280",
    produtividade: "neutral",
    departamento_id: "",
    palavras_chave: [""],
    tier: 3,
  });
  const [editForm, setEditForm] = useState({
    nome: "",
    descricao: "",
    cor: "#6B7280",
    produtividade: "neutral",
    departamento_id: "",
    palavras_chave: [],
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [tags, searchTerm, filterCategoria, filterProdutividade, filterAtivo]);

  const fetchData = async () => {
    try {
      setLoading(true); // Ensure loading is true at the start of fetch
      const [tagsRes, departmentsRes] = await Promise.all([
        api.get("/tags"),
        api.get("/departamentos"),
      ]);

      setTags(tagsRes.data || []);
      setDepartments(departmentsRes.data || []);
      // Apply filters immediately after fetching tags if filters are already set
      applyFilters();
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      setMessage("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const dataToSend = {
        ...formData,
        departamento_id:
          formData.departamento_id === "" ? null : formData.departamento_id,
        palavras_chave: formData.palavras_chave
          .filter((palavra) => palavra.trim())
          .map((palavra) => ({ palavra: palavra.trim(), peso: 1 })),
      };

      if (editingTag) {
        await api.put(`/tags/${editingTag}`, dataToSend);
        setMessage("Tag atualizada com sucesso!");
      } else {
        await api.post("/tags", dataToSend);
        setMessage("Tag criada com sucesso!");
      }

      fetchData(); // Refetch data after successful submission
      resetForm();
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      console.error("Erro ao salvar tag:", error);
      setMessage(
        "Erro ao salvar tag: " +
          (error.response?.data?.message || error.message),
      );
      setTimeout(() => setMessage(""), 5000);
    }
  };

  const handleEdit = (tag) => {
    setEditingTag(tag.id);
    setEditForm({
      nome: tag.nome,
      descricao: tag.descricao || "",
      cor: tag.cor || "#6B7280",
      produtividade: tag.produtividade,
      departamento_id: tag.departamento_id || "",
      palavras_chave: tag.palavras_chave || [],
      tier: tag.tier || 3,
    });
  };

  const handleSaveEdit = async () => {
    setLoading(true);
    try {
      // Preparar dados para envio, tratando campos vazios
      const dataToSend = {
        ...editForm,
        departamento_id:
          editForm.departamento_id === "" ? null : editForm.departamento_id,
        palavras_chave: editForm.palavras_chave
          .filter((palavra) =>
            typeof palavra === "string"
              ? palavra.trim()
              : palavra.palavra?.trim(),
          )
          .map((palavra) => {
            if (typeof palavra === "string") {
              return { palavra: palavra.trim(), peso: 1 };
            }
            return {
              palavra: palavra.palavra?.trim() || "",
              peso: palavra.peso || 1,
            };
          }),
      };

      await api.put(`/tags/${editingTag}`, dataToSend);
      setEditingTag(null);
      fetchData(); // Refetch data after successful submission
      setMessage("Tag atualizada com sucesso!");
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      console.error("Erro ao atualizar tag:", error);
      setMessage(
        "Erro ao atualizar tag: " +
          (error.response?.data?.message || error.message),
      );
      setTimeout(() => setMessage(""), 5000);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (tagId) => {
    if (window.confirm("Tem certeza que deseja excluir esta tag?")) {
      try {
        await api.delete(`/tags/${tagId}`);
        setMessage("Tag excluída com sucesso!");
        fetchData(); // Refetch data after deletion
        setTimeout(() => setMessage(""), 3000);
      } catch (error) {
        console.error("Erro ao excluir tag:", error);
        setMessage("Erro ao excluir tag");
        setTimeout(() => setMessage(""), 3000);
      }
    }
  };

  const resetForm = () => {
    setFormData({
      nome: "",
      descricao: "",
      cor: "#6B7280",
      produtividade: "neutral",
      departamento_id: "",
      palavras_chave: [""],
      tier: 3,
    });
    setEditingTag(null);
    setShowForm(false);
  };

  const addPalavraChave = () => {
    setFormData({
      ...formData,
      palavras_chave: [...formData.palavras_chave, ""],
    });
  };

  const removePalavraChave = (index) => {
    setFormData({
      ...formData,
      palavras_chave: formData.palavras_chave.filter((_, i) => i !== index),
    });
  };

  const updatePalavraChave = (index, value) => {
    const newPalavras = [...formData.palavras_chave];
    newPalavras[index] = value;
    setFormData({
      ...formData,
      palavras_chave: newPalavras,
    });
  };

  const applyFilters = () => {
    let filtered = tags;

    if (searchTerm) {
      filtered = filtered.filter(
        (tag) =>
          tag.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (tag.palavras_chave &&
            tag.palavras_chave.some((palavra) => {
              // Verificar se palavra é string ou objeto
              const palavraText = typeof palavra === 'string' ? palavra : palavra.palavra;
              return palavraText && palavraText.toLowerCase().includes(searchTerm.toLowerCase());
            })),
      );
    }

    if (filterCategoria) {
      filtered = filtered.filter(
        (tag) =>
          tag.categoria &&
          tag.categoria.toLowerCase().includes(filterCategoria.toLowerCase()),
      );
    }

    if (filterProdutividade) {
      filtered = filtered.filter(
        (tag) => tag.produtividade === filterProdutividade,
      );
    }

    if (filterAtivo) {
      const isActive = filterAtivo === "true";
      filtered = filtered.filter((tag) => tag.ativo === isActive);
    }

    setFilteredTags(filtered);
  };

  const handleExportTags = () => {
    const exportData = filteredTags.map((tag) => ({
      Nome: tag.nome,
      Tier: tag.tier || 3,
      Produtividade:
        tag.produtividade === "productive"
          ? "Produtiva"
          : tag.produtividade === "nonproductive"
            ? "Não Produtiva"
            : "Neutra",
      Departamento: tag.departamento_nome || "Global",
      "Palavras-chave":
        tag.palavras_chave?.map((p) => `${p.palavra} (${p.peso})`).join("; ") ||
        "",
      Status: tag.ativo ? "Ativo" : "Inativo",
      Descrição: tag.descricao || "",
    }));

    exportToCSV(exportData, "tags");
  };

  const handlePrintTags = () => {
    const columns = [
      {
        header: "Nome",
        accessor: (row) => row.nome,
      },
      {
        header: "Tier",
        accessor: (row) => `Tier ${row.tier || 3}`,
      },
      {
        header: "Produtividade",
        accessor: (row) =>
          row.produtividade === "productive"
            ? "Produtiva"
            : row.produtividade === "nonproductive"
              ? "Não Produtiva"
              : "Neutra",
        className: (row) => row.produtividade,
      },
      {
        header: "Departamento",
        accessor: (row) => row.departamento_nome || "Global",
      },
      {
        header: "Palavras-chave",
        accessor: (row) =>
          row.palavras_chave
            ?.map((p) => `${p.palavra} (${p.peso})`)
            .join("; ") || "",
      },
      {
        header: "Status",
        accessor: (row) => (row.ativo ? "Ativo" : "Inativo"),
      },
    ];

    printData("Relatório de Tags", filteredTags, columns);
  };

  const handleExportBackup = async () => {
    try {
      const res = await api.get("/tags/export", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.setAttribute("download", "tags_export.csv");
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setMessage("Backup exportado com sucesso!");
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setMessage("Erro ao exportar: " + (err.response?.data?.message || err.message));
      setTimeout(() => setMessage(""), 5000);
    }
  };

  const handleImportCSV = async (e) => {
    const file = e?.target?.files?.[0];
    if (!file) return;
    setImportLoading(true);
    setMessage("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post("/tags/import-csv", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res.data || {};
      const criadas = data.criadas ?? 0;
      const atualizadas = data.atualizadas ?? 0;
      setMessage(`${criadas} tag(s) criada(s), ${atualizadas} atualizada(s).`);
      fetchData();
      if (fileInputRef.current) fileInputRef.current.value = "";
      setTimeout(() => setMessage(""), 5000);
    } catch (err) {
      setMessage("Erro ao importar: " + (err.response?.data?.message || err.message));
      setTimeout(() => setMessage(""), 5000);
    } finally {
      setImportLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-7 p-7">
      {/* Header and Add Button */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Gerenciamento de Tags
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Configure tags para classificação automática de atividades
          </p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={handleExportTags}
            disabled={loading || filteredTags.length === 0}
            className="inline-flex items-center px-3 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
            Exportar CSV
          </button>
          <button
            type="button"
            onClick={handleExportBackup}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
            Exportar backup (CSV completo)
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleImportCSV}
            disabled={importLoading}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={importLoading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
          >
            <ArrowUpTrayIcon className="h-4 w-4 mr-2" />
            {importLoading ? "Importando…" : "Importar do CSV"}
          </button>
          <button
            onClick={handlePrintTags}
            disabled={loading || filteredTags.length === 0}
            className="inline-flex items-center px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            <PrinterIcon className="h-4 w-4 mr-2" />
            Imprimir
          </button>
          {allowEditTags && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            {showForm ? "Cancelar" : "Nova Tag"}
          </button>
          )}
        </div>
      </div>

      {message && (
        <div
          className={`p-4 rounded-md ${message.includes("sucesso") ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}
        >
          {message}
        </div>
      )}

      {/* Search and Filters */}
      <div className="mb-6 bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Buscar
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Nome da tag ou palavra-chave..."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Categoria
            </label>
            <input
              type="text"
              value={filterCategoria}
              onChange={(e) => setFilterCategoria(e.target.value)}
              placeholder="Filtrar por categoria..."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Produtividade
            </label>
            <select
              value={filterProdutividade}
              onChange={(e) => setFilterProdutividade(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="">Todos</option>
              <option value="productive">Produtivo</option>
              <option value="nonproductive">Não Produtivo</option>
              <option value="neutral">Neutro</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Status
            </label>
            <select
              value={filterAtivo}
              onChange={(e) => setFilterAtivo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="">Todos</option>
              <option value="true">Ativo</option>
              <option value="false">Inativo</option>
            </select>
          </div>
        </div>

        <div className="flex justify-between items-center">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Mostrando {filteredTags.length} de {tags.length} tags
          </div>
          <button
            onClick={() => {
              setSearchTerm("");
              setFilterCategoria("");
              setFilterProdutividade("");
              setFilterAtivo("");
            }}
            className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            Limpar Filtros
          </button>
        </div>
      </div>

      {showForm && allowEditTags && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            {editingTag ? "Editar Tag" : "Nova Tag"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Nome da Tag
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) =>
                    setFormData({ ...formData, nome: e.target.value })
                  }
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Produtividade
                </label>
                <select
                  value={formData.produtividade}
                  onChange={(e) =>
                    setFormData({ ...formData, produtividade: e.target.value })
                  }
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="productive">Produtivo</option>
                  <option value="nonproductive">Não Produtivo</option>
                  <option value="neutral">Neutro</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Tier (Prioridade)
                </label>
                <select
                  value={formData.tier}
                  onChange={(e) =>
                    setFormData({ ...formData, tier: parseInt(e.target.value) })
                  }
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="5">5 - Máxima Prioridade</option>
                  <option value="4">4 - Alta Prioridade</option>
                  <option value="3">3 - Prioridade Normal</option>
                  <option value="2">2 - Baixa Prioridade</option>
                  <option value="1">1 - Mínima Prioridade</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Departamento
                </label>
                <select
                  value={formData.departamento_id}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      departamento_id: e.target.value,
                    })
                  }
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Global (Todos os Departamentos)</option>
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.nome}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Cor
                </label>
                <input
                  type="color"
                  value={formData.cor}
                  onChange={(e) =>
                    setFormData({ ...formData, cor: e.target.value })
                  }
                  className="mt-1 block w-full h-10 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Descrição
              </label>
              <textarea
                value={formData.descricao}
                onChange={(e) =>
                  setFormData({ ...formData, descricao: e.target.value })
                }
                rows={3}
                className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Palavras-chave
              </label>
              {formData.palavras_chave.map((palavra, index) => (
                <div key={index} className="flex items-center space-x-2 mb-2">
                  <input
                    type="text"
                    value={palavra}
                    onChange={(e) => updatePalavraChave(index, e.target.value)}
                    placeholder="Digite uma palavra-chave"
                    className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  {formData.palavras_chave.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removePalavraChave(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addPalavraChave}
                className="mt-2 text-sm text-indigo-600 hover:text-indigo-800"
              >
                + Adicionar palavra-chave
              </button>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                {editingTag ? "Atualizar" : "Criar"} Tag
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List of Tags */}
      <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
        {filteredTags && filteredTags.length > 0 ? (
          <table className="min-w-full divide-y divide-gray-300 dark:divide-gray-600">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Nome
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Tier
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Produtividade
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Departamento
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Palavras-chave
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {filteredTags.map((tag) => (
                <tr key={tag.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div
                        className="w-4 h-4 rounded-full mr-3"
                        style={{ backgroundColor: tag.cor }}
                      />
                      {editingTag === tag.id ? (
                        <div className="space-y-2 w-full">
                          <input
                            type="text"
                            value={editForm.nome}
                            onChange={(e) =>
                              setEditForm({ ...editForm, nome: e.target.value })
                            }
                            className="px-2 py-1 border rounded text-sm font-medium"
                            placeholder="Nome da tag"
                          />
                        </div>
                      ) : (
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {tag.nome}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {editingTag === tag.id ? (
                      <select
                        value={editForm.tier || 3}
                        onChange={(e) =>
                          setEditForm({
                            ...editForm,
                            tier: parseInt(e.target.value),
                          })
                        }
                        className="px-2 py-1 border rounded text-sm"
                      >
                        <option value="5">5 - Máxima</option>
                        <option value="4">4 - Alta</option>
                        <option value="3">3 - Normal</option>
                        <option value="2">2 - Baixa</option>
                        <option value="1">1 - Mínima</option>
                      </select>
                    ) : (
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          tag.tier === 5
                            ? "bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100"
                            : tag.tier === 4
                              ? "bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100"
                              : tag.tier === 3
                                ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100"
                                : tag.tier === 2
                                  ? "bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100"
                                  : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
                        }`}
                      >
                        Tier {tag.tier || 3}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {editingTag === tag.id && allowEditTags ? (
                      <select
                        value={editForm.produtividade}
                        onChange={(e) =>
                          setEditForm({
                            ...editForm,
                            produtividade: e.target.value,
                          })
                        }
                        className="px-2 py-1 border rounded text-sm"
                      >
                        <option value="productive">Produtiva</option>
                        <option value="nonproductive">Não Produtiva</option>
                        <option value="neutral">Neutra</option>
                      </select>
                    ) : allowEditTags ? (
                      <button
                        onClick={async () => {
                          const newProductivity =
                            tag.produtividade === "productive"
                              ? "nonproductive"
                              : tag.produtividade === "nonproductive"
                                ? "neutral"
                                : "productive";

                          try {
                            await api.put(`/tags/${tag.id}`, {
                              produtividade: newProductivity,
                            });
                            fetchData();
                            setMessage("Produtividade atualizada com sucesso!");
                            setTimeout(() => setMessage(""), 3000);
                          } catch (error) {
                            console.error(
                              "Erro ao atualizar produtividade:",
                              error,
                            );
                            setMessage("Erro ao atualizar produtividade");
                            setTimeout(() => setMessage(""), 3000);
                          }
                        }}
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full cursor-pointer hover:opacity-80 transition-opacity ${
                          tag.produtividade === "productive"
                            ? "bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100"
                            : tag.produtividade === "nonproductive"
                              ? "bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100"
                              : "bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100"
                        }`}
                      >
                        {tag.produtividade === "productive"
                          ? "Produtiva"
                          : tag.produtividade === "nonproductive"
                            ? "Não Produtiva"
                            : "Neutra"}
                      </button>
                    ) : (
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        tag.produtividade === "productive"
                          ? "bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100"
                          : tag.produtividade === "nonproductive"
                            ? "bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100"
                            : "bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100"
                      }`}>
                        {tag.produtividade === "productive"
                          ? "Produtiva"
                          : tag.produtividade === "nonproductive"
                            ? "Não Produtiva"
                            : "Neutra"}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {tag.departamento_nome || "Global"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex flex-wrap gap-2">
                      {editingTag === tag.id && allowEditTags ? (
                        <div className="space-y-2 w-full">
                          {editForm.palavras_chave.map((palavra, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <input
                                type="text"
                                value={palavra.palavra}
                                onChange={(e) => {
                                  const newPalavras = [
                                    ...editForm.palavras_chave,
                                  ];
                                  newPalavras[idx].palavra = e.target.value;
                                  setEditForm({
                                    ...editForm,
                                    palavras_chave: newPalavras,
                                  });
                                }}
                                className="px-2 py-1 border rounded text-xs"
                                placeholder="Palavra-chave"
                              />
                              <input
                                type="number"
                                value={palavra.peso}
                                onChange={(e) => {
                                  const newPalavras = [
                                    ...editForm.palavras_chave,
                                  ];
                                  newPalavras[idx].peso =
                                    parseInt(e.target.value) || 1;
                                  setEditForm({
                                    ...editForm,
                                    palavras_chave: newPalavras,
                                  });
                                }}
                                className="px-2 py-1 border rounded text-xs w-16"
                                placeholder="Peso"
                                min="1"
                                max="10"
                              />
                              <button
                                onClick={() => {
                                  const newPalavras =
                                    editForm.palavras_chave.filter(
                                      (_, i) => i !== idx,
                                    );
                                  setEditForm({
                                    ...editForm,
                                    palavras_chave: newPalavras,
                                  });
                                }}
                                className="text-red-500 hover:text-red-700"
                              >
                                ✕
                              </button>
                            </div>
                          ))}
                          <button
                            onClick={() => {
                              const newPalavras = [
                                ...editForm.palavras_chave,
                                { palavra: "", peso: 1 },
                              ];
                              setEditForm({
                                ...editForm,
                                palavras_chave: newPalavras,
                              });
                            }}
                            className="text-sm text-blue-500 hover:text-blue-700"
                          >
                            + Adicionar palavra-chave
                          </button>
                        </div>
                      ) : (
                        tag.palavras_chave?.map((palavra, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800"
                          >
                            {palavra.palavra}
                            <span className="ml-1 px-1 bg-blue-200 rounded text-xs">
                              {palavra.peso}
                            </span>
                          </span>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {allowEditTags ? (
                      <button
                        onClick={async () => {
                          try {
                            await api.put(`/tags/${tag.id}`, {
                              ativo: !tag.ativo,
                            });
                            fetchData();
                            setMessage(
                              `Tag ${!tag.ativo ? "ativada" : "desativada"} com sucesso!`,
                            );
                            setTimeout(() => setMessage(""), 3000);
                          } catch (error) {
                            console.error("Erro ao alterar status:", error);
                            setMessage("Erro ao alterar status da tag");
                            setTimeout(() => setMessage(""), 3000);
                          }
                        }}
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full cursor-pointer hover:opacity-80 transition-opacity ${
                          tag.ativo
                            ? "bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100"
                            : "bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100"
                        }`}
                      >
                        {tag.ativo ? "Ativo" : "Inativo"}
                      </button>
                    ) : (
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        tag.ativo
                          ? "bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100"
                          : "bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100"
                      }`}>
                        {tag.ativo ? "Ativo" : "Inativo"}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center space-x-2">
                      {editingTag === tag.id && allowEditTags ? (
                        <>
                          <button
                            onClick={handleSaveEdit}
                            className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                            disabled={loading}
                          >
                            Salvar
                          </button>
                          <button
                            onClick={() => setEditingTag(null)}
                            className="px-3 py-1 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
                          >
                            Cancelar
                          </button>
                        </>
                      ) : (
                        <>
                          {allowEditTags && (
                            <>
                              <button
                                onClick={() => handleEdit(tag)}
                                className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                              >
                                Editar
                              </button>
                              <button
                                onClick={() => handleDelete(tag.id)}
                                className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                                disabled={loading}
                              >
                                Excluir
                              </button>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center py-12 bg-white dark:bg-gray-800">
            <div className="text-gray-400 dark:text-gray-500">
              <svg
                className="mx-auto h-12 w-12 mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a.997.997 0 01-1.414 0l-7-7A1.997 1.997 0 013 12V7a4 4 0 014-4z"
                />
              </svg>
              <p className="text-sm font-medium">
                {searchTerm ||
                filterCategoria ||
                filterProdutividade ||
                filterAtivo
                  ? "Nenhuma tag encontrada com os filtros aplicados"
                  : "Nenhuma tag encontrada"}
              </p>
              <p className="text-xs mt-1">
                {searchTerm ||
                filterCategoria ||
                filterProdutividade ||
                filterAtivo
                  ? "Tente ajustar os filtros ou a busca"
                  : "Crie sua primeira tag para classificar atividades automaticamente"}
              </p>
              {(searchTerm ||
                filterCategoria ||
                filterProdutividade ||
                filterAtivo) && (
                <button
                  onClick={() => {
                    setSearchTerm("");
                    setFilterCategoria("");
                    setFilterProdutividade("");
                    setFilterAtivo("");
                  }}
                  className="mt-4 px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  Limpar filtros e busca
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TagManagement;
