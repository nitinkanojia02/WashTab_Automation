*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${LOGIN_PAGE_URL}    http://172.21.166.115/washtabui/login?data=undefined
${HOME_PAGE_URL}    http://172.21.166.115/washtabui/home
${VALID_USERNAME}    hacklarr
${VALID_PASSWORD}    Icstunnel1
${INVALID_USERNAME}    invaliduser
${INVALID_PASSWORD}    IncorrectPass123
${USERNAME_TEXTBOX}    xpath=//input[@name='ion-input-0']
${PASSWORD_TEXTBOX}    id=password
${SIGN_IN_BUTTON}    xpath=//ion-button[normalize-space()='SIGN IN']
${HOME_NAVIGATION_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='home']]
${BACK_NAVIGATION_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='arrow back']]

*** Keywords ***
Verify Login Page Loaded
    [Documentation]    Verify login page URL and required UI elements are visible and ready for interaction.
    Wait Until Location Is    ${LOGIN_PAGE_URL}    10s
    Wait For Element To Be Ready    ${USERNAME_TEXTBOX}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}
    Wait For Element To Be Ready    ${HOME_NAVIGATION_BUTTON}
    Wait For Element To Be Ready    ${BACK_NAVIGATION_BUTTON}

Enter Username
    [Documentation]    Enter username into username textbox.
    [Arguments]    ${username}
    Input Text When Ready    ${USERNAME_TEXTBOX}    ${username}

Enter Password
    [Documentation]    Enter password into password textbox.
    [Arguments]    ${password}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Clear Element Text    ${PASSWORD_TEXTBOX}
    Input Password    ${PASSWORD_TEXTBOX}    ${password}

Click Sign In Button
    [Documentation]    Click the SIGN IN button.
    Click When Ready    ${SIGN_IN_BUTTON}

Click Home Navigation Button
    [Documentation]    Click the home navigation button from the login page.
    Click When Ready    ${HOME_NAVIGATION_BUTTON}

Click Back Navigation Button
    [Documentation]    Click the back navigation button from the login page.
    Click When Ready    ${BACK_NAVIGATION_BUTTON}

Submit Login With Enter Key
    [Documentation]    Submit the login form using ENTER key from the password field.
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER

Verify Successful Login Redirect
    [Documentation]    Verify successful authentication redirects the user to the home page.
    Wait Until Location Is    ${HOME_PAGE_URL}    10s

Verify Login Failed And Still On Login Page
    [Documentation]    Verify authentication failure keeps the user on the login page.
    Wait Until Location Is    ${LOGIN_PAGE_URL}    10s
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Verify Username Required Validation
    [Documentation]    Verify login attempt without username keeps the user on the login page.
    Wait Until Location Is    ${LOGIN_PAGE_URL}    10s
    Wait For Element To Be Ready    ${USERNAME_TEXTBOX}

Verify Password Required Validation
    [Documentation]    Verify login attempt without password keeps the user on the login page.
    Wait Until Location Is    ${LOGIN_PAGE_URL}    10s
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}

Verify Password Field Is Masked
    [Documentation]    Verify password textbox masks entered characters.
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    ${type}=    Get Element Attribute    ${PASSWORD_TEXTBOX}    type
    Should Be Equal    ${type}    password

Verify Home Navigation Redirects To Home Page
    [Documentation]    Verify clicking home navigation button redirects to home page.
    Wait Until Location Is    ${HOME_PAGE_URL}    10s

Verify Back Navigation Redirects To Home Page
    [Documentation]    Verify clicking back navigation button redirects to home page.
    Wait Until Location Is    ${HOME_PAGE_URL}    10s
