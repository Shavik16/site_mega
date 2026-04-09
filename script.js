const bgMusic = document.getElementById('bgMusic');
const pochitaToast = document.getElementById('pochitaToast');
const muteBtn = document.getElementById('muteBtn');
const keepMusicBtn = document.getElementById('keepMusicBtn');

bgMusic.volume = 0.4;

let musicStarted = false;
function startMusic() {
    if (!musicStarted) {
        bgMusic.play().catch(e => console.log("Браузер ждет взаимодействия пользователя..."));
        musicStarted = true;
    }
}

document.body.addEventListener('click', startMusic, { once: true });
document.body.addEventListener('scroll', startMusic, { once: true });

setTimeout(() => {
    pochitaToast.classList.add('show');
}, 8000);

muteBtn.addEventListener('click', () => {
    bgMusic.pause();
    pochitaToast.classList.remove('show'); 
});

keepMusicBtn.addEventListener('click', () => {
    startMusic(); 
    pochitaToast.classList.remove('show'); 
});

const translations = {
    ru: {
        nav_home: "Главная", nav_works: "Работы", nav_about: "Правила",
        hero_title: "Создаю 3D-миры, которые <span>разрывают</span> шаблоны",
        hero_desc: "Привет, я Щавик. Мой мотор — Blender. Специализируюсь на 3D-анимации, динамике и жесткой эстетике.",
        hero_btn: "Смотреть работы", portfolio_title: "Мои проекты",
        
		card_1_title: "Анимация демона ярости", card_1_desc: "Работа с ригом и эффектом тряски",
		card_2_title: "Появление и удар песчаной руки", card_2_desc: "Разработка анимации способности для Garry's Mod",
		card_3_title: "Падение от пули", card_3_desc: "Работа выполнена за 5 минут для демонстрации скорости",
		card_4_title: "Извлечение катан из ножен", card_4_desc: "Быстрая техническая анимация",

        about_title: "Условия работы & Заказы",
        rule1_title: "1. Четкое ТЗ:", 
        rule1_desc: "Работаю только при наличии понятного ТЗ: идея, референсы (примеры), хронометраж и нужный формат видео.",
        rule2_title: "2. Предоплата:", 
        rule2_desc: "Работа начинается после внесения предоплаты 50%. Это бронирует место в графике и подтверждает серьезность заказа.",
        rule3_title: "3. Исходники:", 
        rule4_title: "4. Пошаговая сборка:", 
        rule4_desc: "Двигаемся этапами: сначала утверждаем эскиз (где что стоит), затем движение (скелет анимации) и в конце — свет и детали. Утвердили этап — идем дальше.",
        rule5_title: "5. Правки:", 
        rule5_desc: "Включено 2 круга бесплатных правок. Важно: правки не должны менять уже утвержденный ранее этап (например, менять сюжет на этапе финала).",
        rule6_title: "6. Финал:", 
        rule6_desc: "Показываю результат с водяным знаком. Чистый файл в полном качестве отдаю сразу после финальной оплаты оставшихся 50%.",
        
        footer_title: "Связь со мной",
        pochita_msg: "Гав! Выключить музыку?", pochita_yes: "Да, вырубай", pochita_no: "Оставь"
    },
    ua: {
        nav_home: "Головна", nav_works: "Роботи", nav_about: "Правила",
        hero_title: "Створюю 3D-світи, що <span>розривають</span> шаблони",
        hero_desc: "Привіт, я Щавик. Мій мотор — Blender. Спеціалізуюся на 3D-анімації, динаміці та жорсткій естетиці.",
        hero_btn: "Дивитись роботи", portfolio_title: "Мої проєкти",
        
		card_1_title: "Анімація демона люті", card_1_desc: "Робота з ригом та ефектом трясіння",
		card_2_title: "Поява та удар піщаної руки", card_2_desc: "Розробка анімації здібності для Garry's Mod",
		card_3_title: "Падіння від кулі", card_3_desc: "Робота виконана за 5 хвилин для демонстрації швидкості",
		card_4_title: "Витягування катан із піхов", card_4_desc: "Швидка технічна анімація",

        about_title: "Умови роботи & Замовлення",
        rule1_title: "1. Чітке ТЗ:", 
        rule1_desc: "Працюю лише за наявності зрозумілого ТЗ: ідея, референси (приклади), хронометраж та потрібний формат відео.",
        rule2_title: "2. Передоплата:", 
        rule2_desc: "Робота починається після внесення передоплати 50%. Це бронює місце в графіку та підтверджує серйозність замовлення.",
        rule3_title: "3. Вихідні дані:", 
        rule3_desc: "Всі логатипи у векторі, шрифти та озвучку потрібно надати до початку анімації, щоб не гальмувати процес.",
        rule4_title: "4. Покрокова збірка:", 
        rule4_desc: "Рухаємося етапами: спочатку схвалюємо ескіз (де що стоїть), потім рух (скелет анімації) і в кінці — світло та деталі. Схвалили етап — йдемо далі.",
        rule5_title: "5. Правки:", 
        rule5_desc: "Включено 2 кола безкоштовних правок. Важливо: правки не мають змінювати вже затверджений етап (наприклад, змінювати сюжет на етапі фіналу).",
        rule6_title: "6. Фінал:", 
        rule6_desc: "Показую результат з водяним знаком. Чистий файл у повній якості віддаю одразу після фінальної оплати залишку 50%.",
        
        footer_title: "Зв'язок зі мною",
        pochita_msg: "Гав! Вимкнути музику?", pochita_yes: "Так, вимикай", pochita_no: "Залиш"
    },
    en: {
        nav_home: "Home", nav_works: "Works", nav_about: "Rules",
        hero_title: "Creating 3D worlds that <span>tear up</span> templates",
        hero_desc: "Hi, I'm Shavik. My engine is Blender. Specializing in 3D animation, dynamics, and hardcore aesthetics.",
        hero_btn: "View Works", portfolio_title: "My Projects",
        
        card_1_title: "Rage demon animation", card_1_desc: "Working with a rig and shaking",
        card_2_title: "The animation of the sand hand appearing and hitting", card_2_desc: "Developing an animation for an ability in Garry's Mod",
        card_3_title: "Fall from a bullet", card_3_desc: "In fact, I did it in about 5 minutes.",
        card_4_title: "Drawing katanas from their sheaths", card_4_desc: "Also done quickly",

        about_title: "Terms & Conditions",
        rule1_title: "1. Clear Brief:", 
        rule1_desc: "I only work with a clear technical brief: idea, references, timing, and the required video format.",
        rule2_title: "2. Prepayment:", 
        rule2_desc: "Work begins after a 50% upfront payment. This secures your spot in my schedule and confirms the order.",
        rule3_title: "3. Assets:", 
        rule3_desc: "Vector logos, fonts, and voiceovers must be provided before animation starts to avoid delays.",
        rule4_title: "4. Step-by-Step:", 
        rule4_desc: "We move in stages: first we approve the sketch (layout), then motion (animation skeleton), and finally — lighting and details.",
        rule5_title: "5. Revisions:", 
        rule5_desc: "2 rounds of revisions are included. Note: edits cannot change a previously approved stage (e.g., changing the plot during the final stage).",
        rule6_title: "6. Final Delivery:", 
        rule6_desc: "I'll show the result with a watermark. The clean, high-quality file is delivered immediately after the final 50% payment.",
        
        footer_title: "Contact Me",
        pochita_msg: "Woof! Mute music?", pochita_yes: "Yes, mute it", pochita_no: "Keep it"
    }
};
function setLang(lang) {
    const elements = document.querySelectorAll('[data-lang]');
    elements.forEach(el => {
        const key = el.getAttribute('data-lang');
        if (translations[lang][key]) {
            el.innerHTML = translations[lang][key];
        }
    });
}