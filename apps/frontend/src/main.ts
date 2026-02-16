import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "@/App.vue";
import { createAppRouter } from "@/app/router";
import { useAuthStore } from "@/features/auth/store/auth_store";
import { bootstrapAuthSession, installAuthAwareFetch } from "@/app/bootstrap/auth_bootstrap";
import "@/styles/main.css";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

const authStore = useAuthStore(pinia);
bootstrapAuthSession(authStore);

const router = createAppRouter(authStore);
installAuthAwareFetch(authStore, router);

app.use(router);
app.mount("#app");
