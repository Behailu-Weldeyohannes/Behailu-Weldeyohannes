<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link
      rel="stylesheet"
      href="https://unpkg.com/boxicons@latest/css/boxicons.min.css"
    />
   
     <script src="https://unpkg.com/scrollreveal"></script>
    
    <style>
      @import url("https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Ubuntu:wght@400;500;700&display=swap");

:root {
  --box-shadow: 10px 10px 30px rgba(0, 109, 175, 0.2);
  --color-mwhite: #fff;
  --color-dark: #525252;
  --color-black: #000;
  /* --transition: all 300ms ease; */
  --color-bgmain: #00539cff;
  
  --color-bgmain-light: #9469cc;
  --color-text1: #eea47fff;
  
}

/* General styling */



section .title {
  position: relative;
  text-align: left;
  font-size: 36px;
  font-weight: 500;
  margin-bottom: 50px;
  padding-bottom: 10px;
  font-family: "Poppins", sans-serif;
}
.social-icons {
  display: grid;
  margin-top: 3rem;
  width: 20rem;
  grid-template-columns: repeat(3, 1fr);
  /* justify-items: center; */
  font-size: 1.5rem;

}
.social-icon {
  font-size: 1.5rem;
  color: var(--color-text1);
  -webkit-transition: var(--transition);
  transition: var(--transition);
}
.social-icon:hover {
  color: var(--color-dark);
}




.btn-01 {
  display: inline-block;
  background: var(--color-bgmain);
  color: var(--color-mwhite);
  font-size: 20px;
  font-weight: 500;
  padding: 10px 30px;
  margin-top: 10px;
  border-radius: 6px;

  border: 2px solid var(--color-text1);
  transition: all 0.3s ease;
}
.btn-01:hover {
  color: var(--color-text1);
  background: none;
}
    </style>
</head>
<body>
  
<section class="about" id="about">
        <div class="container-width">
            <h2 class="title">About me</h2>
            <div class="about-content">
                
                <div class="column right">
                    
                    <p>
                      I am a Software and MuleSoft Developer. With a strong foundation in programming languages, I can deliver efficient and effective solutions that meet clients' requirements. 
I am great at troubleshooting complex software issues and have the ability to think outside the box when it comes to creative solutions.
<br>
In addition to my technical skills, I am also a committed human rights lawyer with experience working on various cases, ranging from gender-based violence to freedom of expression.
I am excited to explore new opportunities and take on new challenges to develop my skills and grow professionally.
If you are looking for a motivated and multifaceted Software or MuleSoft Developer, I would love to hear about potential opportunities.
                        </p>
                        <br>
                        <p> <strong>Skills:</strong> <small><i class="italic"> JavaScript | React | HTML | CSS | Figma | Adobe XD | Node | Vite | Git and Github | prettier | web components | PWA | Rest API | material ui | Index DB | Bootstrap | My SQL | MS SQL | Tailwind | webflow </i> </small></p>
                    <a href="https://behailu-weldeyohannes.github.io/portfolio/" target="_blank" rel="noopener noreferrer">View my portfolio</a>
                </div>
            </div>
        </div>
    </section>
<div class="social">
                         <a href="https://github.com/behailu2021" target="_blank" rel="noopener noreferrer">
            <i class="bx bxl-github bx-flashing"></i></a>
                        <a href="https://www.linkedin.com/in/beha" target="_blank" rel="noopener noreferrer" class="social-icon">
            <i class="bx bxl-linkedin-square bx-flashing"></i></a>
         <a href="https://twitter.com/BehailuW" target="_blank" rel="noopener noreferrer" class="social-icon">
            
            <i class="bx bxl-twitter bx-flashing"></i></a>
        </div>
  
    <script>

const sr = ScrollReveal({
  distance: "45px",
  duration: 2700,
  reset: true,
});

sr.reveal(".home-text", { delay: 350, origin: "left" });
sr.reveal(".home-img", { delay: 350, origin: "right" });
sr.reveal(".sub-service, .about, .portfolio, .services, .projects , .contact", {
  delay: 200,
  origin: "bottom",
});
    </script> 
</body>
</html>
