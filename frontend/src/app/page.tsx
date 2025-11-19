"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";
const API_ROOT = API_BASE.replace(/\/api\/?$/, "");

type Product = {
  id: string;
  sku: string;
  name: string;
  description?: string | null;
  active: boolean;
};

type ProductResponse = {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

type Webhook = {
  id: string;
  url: string;
  event_type: string;
  enabled: boolean;
};

type UploadProgress = {
  progress: number;
  status: "pending" | "processing" | "success" | "failure";
  message?: string;
  rows_processed?: number;
  rows_total?: number | null;
  products_processed?: number;
  processing_speed?: number;
  eta_seconds?: number | null;
  error_count?: number;
};

const EVENT_TYPES = [
  "product.created",
  "product.updated",
  "product.deleted",
  "product.bulk_import",
  "product.bulk_delete",
];

const TABS = [
  { id: "upload", label: "Upload CSV" },
  { id: "products", label: "Products" },
  { id: "webhooks", label: "Webhooks" },
];

const DEFAULT_FILTERS = {
  sku: "",
  name: "",
  description: "",
  active: "",
};

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<string>("upload");

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(
    null
  );

  // Notifications
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Products
  const [products, setProducts] = useState<Product[]>([]);
  const [productResponse, setProductResponse] = useState<ProductResponse>({
    items: [],
    total: 0,
    page: 1,
    page_size: 50,
    total_pages: 1,
  });
  const [productFilters, setProductFilters] =
    useState<typeof DEFAULT_FILTERS>(DEFAULT_FILTERS);
  const [loadingProducts, setLoadingProducts] = useState(false);

  const [showProductModal, setShowProductModal] = useState(false);
  const [productModalMode, setProductModalMode] = useState<"create" | "edit">(
    "create"
  );
  const [productForm, setProductForm] = useState({
    id: "",
    sku: "",
    name: "",
    description: "",
    active: true,
  });
  const [productFormLoading, setProductFormLoading] = useState(false);

  // Webhooks
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loadingWebhooks, setLoadingWebhooks] = useState(false);
  const [showWebhookModal, setShowWebhookModal] = useState(false);
  const [webhookForm, setWebhookForm] = useState({
    id: "",
    url: "",
    event_type: EVENT_TYPES[0],
    enabled: true,
  });
  const [webhookFormLoading, setWebhookFormLoading] = useState(false);

  const notify = useCallback((type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  }, []);

  const fetchProducts = useCallback(
    async (page = 1) => {
      setLoadingProducts(true);
      try {
        const params = new URLSearchParams({
          page: page.toString(),
          page_size: productResponse.page_size.toString(),
        });
        Object.entries(productFilters).forEach(([key, value]) => {
          if (value) {
            params.append(key, value);
          }
        });

        const res = await fetch(`${API_BASE}/products/?${params.toString()}`);
        if (!res.ok) throw new Error("Failed to fetch products");
        const data: ProductResponse = await res.json();
        setProducts(data.items);
        setProductResponse(data);
      } catch (error) {
        console.error(error);
        notify("error", "Unable to fetch products");
      } finally {
        setLoadingProducts(false);
      }
    },
    [notify, productFilters, productResponse.page_size]
  );

  const fetchWebhooks = useCallback(async () => {
    setLoadingWebhooks(true);
    try {
      const res = await fetch(`${API_BASE}/webhooks/`);
      if (!res.ok) throw new Error("Failed to fetch webhooks");
      const data: Webhook[] = await res.json();
      setWebhooks(data);
    } catch (error) {
      console.error(error);
      notify("error", "Unable to fetch webhooks");
    } finally {
      setLoadingWebhooks(false);
    }
  }, [notify]);

  useEffect(() => {
    if (activeTab === "products") {
      fetchProducts(1);
    }
    if (activeTab === "webhooks") {
      fetchWebhooks();
    }
  }, [activeTab, fetchProducts, fetchWebhooks]);

  const resetProductForm = () => {
    setProductForm({
      id: "",
      sku: "",
      name: "",
      description: "",
      active: true,
    });
  };

  const resetWebhookForm = () => {
    setWebhookForm({
      id: "",
      url: "",
      event_type: EVENT_TYPES[0],
      enabled: true,
    });
  };

  const handleFileChange = (file?: File) => {
    if (file && !file.name.endsWith(".csv")) {
      notify("error", "Please select a CSV file");
      return;
    }
    setSelectedFile(file ?? null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append("file", selectedFile);
    setIsUploading(true);

    // Show upload progress
    setUploadProgress({
      progress: 0,
      status: "pending",
      message: "Uploading file...",
    });

    try {
      // Use XMLHttpRequest for upload progress tracking
      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          const uploadProgress = Math.round((e.loaded / e.total) * 100);
          setUploadProgress({
            progress: Math.min(uploadProgress, 90), // Cap at 90% during upload
            status: "pending",
            message: `Uploading file... ${uploadProgress}%`,
          });
        }
      });

      // Wait for upload to complete
      await new Promise<void>((resolve, reject) => {
        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            try {
              const error = JSON.parse(xhr.responseText);
              reject(new Error(error.detail || "Upload failed"));
            } catch {
              reject(new Error("Upload failed"));
            }
          }
        });

        xhr.addEventListener("error", () => {
          reject(new Error("Upload failed"));
        });

        xhr.open("POST", `${API_BASE}/upload/`);
        xhr.send(formData);
      });

      const data = JSON.parse(xhr.responseText);
      const taskId = data.task_id;

      // Update to processing status
      setUploadProgress({
        progress: 5,
        status: "processing",
        message: "File uploaded. Starting processing...",
      });

      const es = new EventSource(`${API_ROOT}/api/progress/${taskId}`);

      es.onmessage = (event) => {
        if (!event.data) return;
        const payload = JSON.parse(event.data);
        setUploadProgress({
          progress: payload.progress ?? 0,
          status: payload.status ?? "processing",
          message: payload.message,
          rows_processed: payload.rows_processed ?? 0,
          rows_total: payload.rows_total ?? null,
          products_processed: payload.products_processed ?? 0,
          processing_speed: payload.processing_speed ?? 0,
          eta_seconds: payload.eta_seconds ?? null,
          error_count: payload.error_count ?? 0,
        });
        if (payload.status === "success") {
          notify(
            "success",
            payload.message || "Import completed successfully."
          );
          es.close();
          setIsUploading(false);
          setSelectedFile(null);
          if (activeTab === "products") {
            fetchProducts(productResponse.page);
          }
        } else if (payload.status === "failure") {
          notify("error", payload.message || "Import failed");
          es.close();
          setIsUploading(false);
        }
      };

      es.onerror = () => {
        notify("error", "Connection lost. Please check Celery worker.");
        es.close();
        setIsUploading(false);
        setUploadProgress({
          progress: 0,
          status: "failure",
          message: "Connection lost. Please check Celery worker.",
        });
      };
    } catch (error) {
      notify("error", getErrorMessage(error, "Upload failed"));
      setIsUploading(false);
      setUploadProgress({
        progress: 0,
        status: "failure",
        message: getErrorMessage(error, "Upload failed"),
      });
    }
  };

  const submitProductForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setProductFormLoading(true);
    const payload = {
      sku: productForm.sku.trim(),
      name: productForm.name.trim(),
      description: productForm.description.trim(),
      active: productForm.active,
    };

    try {
      const url =
        productModalMode === "edit"
          ? `${API_BASE}/products/${productForm.id}`
          : `${API_BASE}/products/`;
      const method = productModalMode === "edit" ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || "Product save failed");
      }
      notify(
        "success",
        productModalMode === "edit"
          ? "Product updated successfully"
          : "Product created successfully"
      );
      setShowProductModal(false);
      resetProductForm();
      fetchProducts(productResponse.page);
    } catch (error) {
      notify("error", getErrorMessage(error, "Unable to save product"));
    } finally {
      setProductFormLoading(false);
    }
  };

  const handleDeleteProduct = async (id: string) => {
    if (!confirm("Delete this product?")) return;
    try {
      const res = await fetch(`${API_BASE}/products/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete product");
      notify("success", "Product deleted");
      fetchProducts(productResponse.page);
    } catch (error) {
      notify("error", getErrorMessage(error, "Unable to delete product"));
    }
  };

  const handleBulkDelete = async () => {
    if (
      !confirm(
        "Are you sure you want to delete ALL products? This is permanent."
      )
    )
      return;
    try {
      const res = await fetch(`${API_BASE}/products/`, { method: "DELETE" });
      if (!res.ok) throw new Error("Bulk delete failed");
      const data = await res.json();
      notify("success", data.message || "Products deleted");
      fetchProducts(1);
    } catch (error) {
      notify("error", getErrorMessage(error, "Bulk delete failed"));
    }
  };

  const submitWebhookForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setWebhookFormLoading(true);
    const payload = {
      url: webhookForm.url.trim(),
      event_type: webhookForm.event_type,
      enabled: webhookForm.enabled,
    };

    try {
      const url = webhookForm.id
        ? `${API_BASE}/webhooks/${webhookForm.id}`
        : `${API_BASE}/webhooks/`;
      const method = webhookForm.id ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Webhook save failed");
      notify("success", webhookForm.id ? "Webhook updated" : "Webhook created");
      setShowWebhookModal(false);
      resetWebhookForm();
      fetchWebhooks();
    } catch (error) {
      notify("error", getErrorMessage(error, "Unable to save webhook"));
    } finally {
      setWebhookFormLoading(false);
    }
  };

  const handleDeleteWebhook = async (id: string) => {
    if (!confirm("Delete this webhook?")) return;
    try {
      const res = await fetch(`${API_BASE}/webhooks/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete webhook");
      notify("success", "Webhook deleted");
      fetchWebhooks();
    } catch (error) {
      notify("error", getErrorMessage(error, "Unable to delete webhook"));
    }
  };

  const handleTestWebhook = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/webhooks/${id}/test`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Test failed");
      const data = await res.json();
      notify(
        data.success ? "success" : "error",
        data.success
          ? `Webhook responded in ${data.response_time_ms?.toFixed(2)}ms`
          : data.error || "Webhook test failed"
      );
    } catch (error) {
      notify("error", getErrorMessage(error, "Webhook test failed"));
    }
  };

  const ProductFilters = (
    <div className="filters">
      <input
        value={productFilters.sku}
        placeholder="SKU"
        onChange={(e) =>
          setProductFilters((prev) => ({ ...prev, sku: e.target.value }))
        }
      />
      <input
        value={productFilters.name}
        placeholder="Name"
        onChange={(e) =>
          setProductFilters((prev) => ({ ...prev, name: e.target.value }))
        }
      />
      <input
        value={productFilters.description}
        placeholder="Description"
        onChange={(e) =>
          setProductFilters((prev) => ({
            ...prev,
            description: e.target.value,
          }))
        }
      />
      <select
        value={productFilters.active}
        onChange={(e) =>
          setProductFilters((prev) => ({ ...prev, active: e.target.value }))
        }
      >
        <option value="">All</option>
        <option value="true">Active</option>
        <option value="false">Inactive</option>
      </select>
      <button
        className="primary"
        onClick={() => {
          fetchProducts(1);
        }}
      >
        Filter
      </button>
      <button
        className="ghost"
        onClick={() => {
          setProductFilters(DEFAULT_FILTERS);
          fetchProducts(1);
        }}
      >
        Clear
      </button>
    </div>
  );

  const Pagination = (
    <div className="pagination">
      <button
        disabled={productResponse.page <= 1}
        onClick={() => fetchProducts(productResponse.page - 1)}
      >
        Previous
      </button>
      <span>
        Page {productResponse.page} / {productResponse.total_pages} —{" "}
        {productResponse.total} products
      </span>
      <button
        disabled={productResponse.page >= productResponse.total_pages}
        onClick={() => fetchProducts(productResponse.page + 1)}
      >
        Next
      </button>
    </div>
  );

  const ProductModal = (
    <Modal
      open={showProductModal}
      onClose={() => {
        setShowProductModal(false);
        resetProductForm();
      }}
      title={productModalMode === "edit" ? "Edit Product" : "Create Product"}
    >
      <form className="modal-form" onSubmit={submitProductForm}>
        <label>
          SKU
          <input
            value={productForm.sku}
            onChange={(e) =>
              setProductForm((prev) => ({ ...prev, sku: e.target.value }))
            }
            required
            disabled={productModalMode === "edit"}
          />
        </label>
        <label>
          Name
          <input
            value={productForm.name}
            onChange={(e) =>
              setProductForm((prev) => ({ ...prev, name: e.target.value }))
            }
            required
          />
        </label>
        <label>
          Description
          <textarea
            value={productForm.description}
            onChange={(e) =>
              setProductForm((prev) => ({
                ...prev,
                description: e.target.value,
              }))
            }
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={productForm.active}
            onChange={(e) =>
              setProductForm((prev) => ({ ...prev, active: e.target.checked }))
            }
          />
          Active
        </label>
        <button className="primary" type="submit" disabled={productFormLoading}>
          {productFormLoading ? "Saving..." : "Save"}
        </button>
      </form>
    </Modal>
  );

  const WebhookModal = (
    <Modal
      open={showWebhookModal}
      onClose={() => {
        setShowWebhookModal(false);
        resetWebhookForm();
      }}
      title={webhookForm.id ? "Edit Webhook" : "Add Webhook"}
    >
      <form className="modal-form" onSubmit={submitWebhookForm}>
        <label>
          URL
          <input
            value={webhookForm.url}
            onChange={(e) =>
              setWebhookForm((prev) => ({ ...prev, url: e.target.value }))
            }
            required
            type="url"
            placeholder="https://example.com/webhook"
          />
        </label>
        <label>
          Event Type
          <select
            value={webhookForm.event_type}
            onChange={(e) =>
              setWebhookForm((prev) => ({
                ...prev,
                event_type: e.target.value,
              }))
            }
          >
            {EVENT_TYPES.map((event) => (
              <option key={event} value={event}>
                {event}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={webhookForm.enabled}
            onChange={(e) =>
              setWebhookForm((prev) => ({
                ...prev,
                enabled: e.target.checked,
              }))
            }
          />
          Enabled
        </label>
        <button className="primary" type="submit" disabled={webhookFormLoading}>
          {webhookFormLoading ? "Saving..." : "Save"}
        </button>
      </form>
    </Modal>
  );

  return (
    <div className="page">
      <header>
        <div>
          <h1>Product Importer</h1>
          <p>Upload products, manage catalog, and configure webhooks.</p>
        </div>
        <span className="badge">FastAPI + Celery + Next.js</span>
      </header>

      <nav className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={tab.id === activeTab ? "active" : ""}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {notification && (
        <div className={`toast ${notification.type}`}>
          {notification.message}
        </div>
      )}

      <section hidden={activeTab !== "upload"}>
        <div className="card">
          <div className="card-header">
            <h2>Upload CSV</h2>
            <p>Select up to 500,000 products (CSV format).</p>
          </div>
          <div className="upload-box">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => handleFileChange(e.target.files?.[0])}
            />
            {selectedFile && (
              <div className="file-info">
                <strong>{selectedFile.name}</strong>
                <span>{(selectedFile.size / 1024).toFixed(1)} KB</span>
              </div>
            )}
            <button
              className="primary"
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
            >
              {isUploading ? "Uploading..." : "Start Upload"}
            </button>
          </div>
          {uploadProgress && (
            <div className="progress-container">
              <div className="progress-header">
                <span className="progress-title">
                  {uploadProgress.status === "processing" && "⏳ Processing..."}
                  {uploadProgress.status === "success" && "✅ Complete"}
                  {uploadProgress.status === "failure" && "❌ Failed"}
                  {uploadProgress.status === "pending" && "⏳ Waiting..."}
                </span>
                <span className="progress-percentage">
                  {uploadProgress.progress}%
                </span>
              </div>
              <div className="progress-bar">
                <div
                  className={`progress-fill ${uploadProgress.status}`}
                  style={{ width: `${uploadProgress.progress}%` }}
                />
              </div>
              <div className="progress-stats">
                {uploadProgress.rows_processed !== undefined && (
                  <div className="stat-item">
                    <span className="stat-label">Rows:</span>
                    <span className="stat-value">
                      {uploadProgress.rows_processed.toLocaleString()}
                      {uploadProgress.rows_total &&
                        ` / ${uploadProgress.rows_total.toLocaleString()}`}
                    </span>
                  </div>
                )}
                {uploadProgress.products_processed !== undefined &&
                  uploadProgress.products_processed > 0 && (
                    <div className="stat-item">
                      <span className="stat-label">Products:</span>
                      <span className="stat-value">
                        {uploadProgress.products_processed.toLocaleString()}
                      </span>
                    </div>
                  )}
                {uploadProgress.processing_speed !== undefined &&
                  uploadProgress.processing_speed > 0 && (
                    <div className="stat-item">
                      <span className="stat-label">Speed:</span>
                      <span className="stat-value">
                        {Math.round(
                          uploadProgress.processing_speed
                        ).toLocaleString()}{" "}
                        rows/sec
                      </span>
                    </div>
                  )}
                {uploadProgress.eta_seconds !== null &&
                  uploadProgress.eta_seconds !== undefined &&
                  uploadProgress.eta_seconds > 0 && (
                    <div className="stat-item">
                      <span className="stat-label">ETA:</span>
                      <span className="stat-value">
                        {uploadProgress.eta_seconds < 60
                          ? `${uploadProgress.eta_seconds}s`
                          : uploadProgress.eta_seconds < 3600
                          ? `${Math.floor(uploadProgress.eta_seconds / 60)}m ${
                              uploadProgress.eta_seconds % 60
                            }s`
                          : `${Math.floor(
                              uploadProgress.eta_seconds / 3600
                            )}h ${Math.floor(
                              (uploadProgress.eta_seconds % 3600) / 60
                            )}m`}
                      </span>
                    </div>
                  )}
                {uploadProgress.error_count !== undefined &&
                  uploadProgress.error_count > 0 && (
                    <div className="stat-item error">
                      <span className="stat-label">Errors:</span>
                      <span className="stat-value">
                        {uploadProgress.error_count}
                      </span>
                    </div>
                  )}
              </div>
              {uploadProgress.message && (
                <div className="progress-message">{uploadProgress.message}</div>
              )}
            </div>
          )}
        </div>
      </section>

      <section hidden={activeTab !== "products"}>
        <div className="card">
          <div className="card-header">
            <h2>Product Management</h2>
            <div className="actions">
              <button
                className="primary"
                onClick={() => {
                  resetProductForm();
                  setProductModalMode("create");
                  setShowProductModal(true);
                }}
              >
                New Product
              </button>
              <button className="danger" onClick={handleBulkDelete}>
                Delete All
              </button>
            </div>
          </div>
          {ProductFilters}
          {loadingProducts ? (
            <p>Loading products...</p>
          ) : products.length === 0 ? (
            <p>No products found.</p>
          ) : (
            <div className="list-grid">
              {products.map((product) => (
                <div key={product.id} className="list-card">
                  <div>
                    <h3>
                      {product.name}{" "}
                      <span className="muted">({product.sku})</span>
                    </h3>
                    <p>{product.description || "No description"}</p>
                    <span
                      className={`status ${product.active ? "active" : ""}`}
                    >
                      {product.active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  <div className="row-actions">
                    <button
                      className="ghost"
                      onClick={() => {
                        setProductModalMode("edit");
                        setProductForm({
                          id: product.id,
                          sku: product.sku,
                          name: product.name,
                          description: product.description ?? "",
                          active: product.active,
                        });
                        setShowProductModal(true);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="danger ghost"
                      onClick={() => handleDeleteProduct(product.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {Pagination}
        </div>
      </section>

      <section hidden={activeTab !== "webhooks"}>
        <div className="card">
          <div className="card-header">
            <h2>Webhooks</h2>
            <button
              className="primary"
              onClick={() => {
                resetWebhookForm();
                setShowWebhookModal(true);
              }}
            >
              Add Webhook
            </button>
          </div>
          {loadingWebhooks ? (
            <p>Loading webhooks...</p>
          ) : webhooks.length === 0 ? (
            <p>No webhooks configured yet.</p>
          ) : (
            <div className="list-grid">
              {webhooks.map((webhook) => (
                <div key={webhook.id} className="list-card">
                  <div>
                    <h3>{webhook.url}</h3>
                    <p>
                      Event: <strong>{webhook.event_type}</strong>
                    </p>
                    <span
                      className={`status ${webhook.enabled ? "active" : ""}`}
                    >
                      {webhook.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                  <div className="row-actions wrap">
                    <button
                      className="ghost"
                      onClick={() => {
                        setWebhookForm({
                          id: webhook.id,
                          url: webhook.url,
                          event_type: webhook.event_type,
                          enabled: webhook.enabled,
                        });
                        setShowWebhookModal(true);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="ghost"
                      onClick={() => handleTestWebhook(webhook.id)}
                    >
                      Test
                    </button>
                    <button
                      className="danger ghost"
                      onClick={() => handleDeleteWebhook(webhook.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {ProductModal}
      {WebhookModal}
    </div>
  );
}

type ModalProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
};

function Modal({ open, onClose, title, children }: ModalProps) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button onClick={onClose}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}
