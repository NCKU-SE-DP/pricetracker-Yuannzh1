<template>
    <nav class="navbar" :class="{ 'isMenuOpen': isMenuOpen }">
        <div class="title">
            <RouterLink to="/overview">價格追蹤小幫手</RouterLink>
        </div>
        <div class="menu-icon" @click="toggleMenu">
            <div></div>
            <div></div>
            <div></div>
        </div>
        <ul class="options">
            <li><RouterLink to="/overview">物價概覽</RouterLink></li>
            <li><RouterLink to="/trending">物價趨勢</RouterLink></li>
            <li><RouterLink to="/news">相關新聞</RouterLink></li>
            <li v-if="!isLoggedIn"><RouterLink to="/login">登入</RouterLink></li>
            <li v-else @click="logout">Hi, {{getUserName}}! 登出</li>
        </ul>
    </nav>
</template>

<script>
import { useAuthStore } from '@/stores/auth';

export default {
    name: 'NavBar',
    data() {
        return {
            isMenuOpen: false,
        };
    },
    computed: {
        isLoggedIn(){
            const userStore = useAuthStore();
            return userStore.isLoggedIn;
        },
        getUserName(){
            const userStore = useAuthStore();
            return userStore.getUserName;
        }
    },
    methods: {
        logout(){
            const userStore = useAuthStore();
            userStore.logout();
        },
        toggleMenu() {
            this.isMenuOpen = !this.isMenuOpen;
        }
    }
};
</script>

<style scoped>
/* 通用樣式 */
.navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #f3f3f3;
    padding: 1.5em;
    box-shadow: 0 0 5px #000000;
    position: relative;
}
.title > a {
    font-size: 1.4em;
    font-weight: bold;
    color: #2c3e50 !important;
}
/*
.menu-icon {
    display: none;  隱藏漢堡圖示，除非是小螢幕 
}*/

.options {
    list-style: none;
    display: flex;
    padding: 0;
}

.navbar li {
    color: #202223;
    margin: 0 .5em;
    font-size: 1.2em;
}

.navbar li:hover {
    cursor: pointer;
    font-weight: bold;
}

.navbar a {
    text-decoration: none;
    color: #575B5D;
}

/* 移動設備樣式 */
@media (max-width: 768px) {
    .navbar {
        flex-direction: column;
        align-items: flex-start;
    }

    .title {
        width: 100%;
        text-align: center;
    }

    .menu-icon {
        display: inline-flex;
        cursor: pointer;
        flex-direction: column;
        justify-content: space-around;
        height: 32px;
        width: 36px;
        position: absolute;
        top: 20px;
        right: 20px;
    }

    .menu-icon div {
        width: 100%;
        height: 3px;
        background-color: black;
        margin: 2px 0;
    }

    .options {
        display: none; /* 默認隱藏選單 */
        flex-direction: column;
        width: 100%;
        margin-top: 10px;
        align-items: center;
        background-color: #f3f3f3;
    }

    .options li {
        width: 100%;
        padding: 1em;
        /*text-align: center;*/
        margin: 0 0;
        border-bottom: 2px solid #ddd;
    }

    .options li:last-child {
        border-bottom: none;
    }

    .isMenuOpen .options {
        display: flex; /* 漢堡選單點擊時顯示選單 */
    }
}

/* 桌面版樣式 */
@media (min-width: 769px) {
    .options {
        display: flex;
        flex-direction: row; /* 水平排列選單 */
        justify-content: flex-end;
    }

    .options li {
        margin-left: 20px;
        padding: 0;
        border-bottom: none;
    }

    .menu-icon {
        display: none; /* 隱藏漢堡選單 */
    }
}

</style>