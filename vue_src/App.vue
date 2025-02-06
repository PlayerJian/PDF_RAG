<template>
  <div id="app">
    <img src="./assets/image.png" alt="Code Interpreter Logo" class="logo">
    <RAGDemo />
  </div>
</template>

<script>
import RAGDemo from './components/RAGDemo.vue'

export default {
  name: 'App',
  components: {
    RAGDemo
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
.logo {
  width: 80px;
  height: 80px;
}
</style>
