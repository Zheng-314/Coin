import{ defineStore } from 'pinia'
import {ref,computed } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router';

// 定义名为‘auth' 的store
export const useAuthStore = defineStore('auth',() =>{
    // State 
    const token = ref(localStorage.getItem('token')|| null);
    const user = ref(JSON.parse(localStorage.getItem('user'))|| null)
    const router = useRouter();

    // Getters 检测到不一样就更新
    const isAuthenticated = computed(()=> !!token.value);
    const username = computed(()=> user.value?.username);

    // Actions
    // token相当于身份证 这里就是给每个API请求加上这个token保证请求能够被识别（通过axios发送请求）；如果没有token就设置为null
    const setTokenInHeaders=() =>{
        if(token.value){
            axios.defaults.headers.common['Authorization'] = token.value;
        }
        else{
            delete axios.defaults.headers.common['Authorization'];
        }
    }

    const login = (userData) =>{
        token.value = userData.token;
        user.value = {id: userData.id, username: userData.username };

        localStorage.setItem('token',token.value);
        localStorage.setItem('user',JSON.stringify(user.value));

        setTokenInHeaders();
        router.push('/');
    }

    const logout =(redirect = true) =>{
        token.value = null;
        user.value = null;

        localStorage.removeItem('token');
        localStorage.removeItem('user');

        setTokenInHeaders();
        if(redirect){
            router.push('/login')
        }
    }

    // 如果用户已经登陆 刷新一次后 不带这个的话 刷新后发起的第一个API请求就会因为没有携带token而失败
    setTokenInHeaders();

    return {token,user,isAuthenticated,username,login,logout};
});