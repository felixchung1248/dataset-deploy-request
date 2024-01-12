resource "helm_release" "request-dataset-deploy" {
  name       = "request-dataset-deploy"
  chart      = "/chart"
  namespace  = "request-dataset-deploy-ns"
  create_namespace = true
}