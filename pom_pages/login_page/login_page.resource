*** Settings ***
Library    SeleniumLibrary

*** Variables ***
${USER_NAME_TEXTBOX}    xpath=//input[@placeholder='User Name']
${PASSWORD_TEXTBOX}     xpath=//input[@placeholder='Password']
${SIGN_IN_BUTTON}       xpath=//ion-button[normalize-space(.)='SIGN IN']

${VALID_USERNAME}       haklarr
${VALID_PASSWORD}       Icstunnel1
${INVALID_USERNAME}     invalid_user
${INVALID_PASSWORD}     wrong_password
${BLANK_USERNAME}       ${EMPTY}
${BLANK_PASSWORD}       ${EMPTY}

*** Keywords ***
Enter User Name Textbox
    [Arguments]    ${text}
    Wait Until Element Is Visible    ${USER_NAME_TEXTBOX}    10s
    Input Text    ${USER_NAME_TEXTBOX}    ${text}

Enter Password Textbox
    [Arguments]    ${text}
    Wait Until Element Is Visible    ${PASSWORD_TEXTBOX}    10s
    Input Text    ${PASSWORD_TEXTBOX}    ${text}

Click Sign In Button
    Wait Until Element Is Visible    ${SIGN_IN_BUTTON}    10s
    Click Element    ${SIGN_IN_BUTTON}

Verify Login Page Loaded
    Wait Until Element Is Visible    ${USER_NAME_TEXTBOX}    10s
    Wait Until Element Is Visible    ${PASSWORD_TEXTBOX}    10s
    Wait Until Element Is Visible    ${SIGN_IN_BUTTON}    10s

Verify Login Failed
    Wait Until Element Is Visible    ${SIGN_IN_BUTTON}    10s
    Wait Until Element Is Visible    ${USER_NAME_TEXTBOX}    10s
    Wait Until Element Is Visible    ${PASSWORD_TEXTBOX}    10s
